from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.models import (
    Message,
    MessageRole,
    Payment,
    ProductUsage,
    SoulProfile,
    TarotCard,
    TarotReading,
    User,
    WebCardOverride,
    WebIdentity,
    WebMatrixCache,
    WebReading,
    WebSession,
)
from app.services.ai.kie_client import KieClient
from app.services.billing.robokassa_client import RobokassaNotConfiguredError, build_payment_url, next_invoice_id
from app.services.web.catalog import CARDS, WebCard, apply_override, public_card
from app.services.web.mini import build_mini

logger = logging.getLogger(__name__)

READING_TTL = timedelta(days=366)
READING_CHAT_LIMIT = 10
BANNED = ("суицид", "беремен", "диагноз", "смерть", "юридическ", "лечение", "аборт")


def _parse_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _fmt_birth(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value else ""


async def upsert_soul_profile(
    session: AsyncSession,
    user: User,
    *,
    name: str | None = None,
    birth: str | date | None = None,
    birth_city: str | None = None,
    birth_time: str | None = None,
    overwrite: bool = False,
) -> SoulProfile:
    profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
    if profile is None:
        profile = SoulProfile(user_id=user.id)
        session.add(profile)
        await session.flush()

    if name is not None:
        cleaned = name.strip()
        if overwrite:
            profile.name = cleaned[:255] or None
            if cleaned:
                user.first_name = cleaned[:255]
        elif cleaned and not profile.name:
            profile.name = cleaned[:255]
            if not user.first_name or user.first_name in {"Гость сайта", "Лея"}:
                user.first_name = cleaned[:255]

    if isinstance(birth, date):
        parsed = birth
        empty = False
    else:
        raw = (birth or "").strip() if birth is not None else None
        empty = birth is not None and not raw
        parsed = _parse_date(raw) if raw else None
    if overwrite and empty:
        profile.birth_date = None
    elif parsed and (overwrite or not profile.birth_date):
        profile.birth_date = parsed

    if birth_city is not None:
        city = birth_city.strip()
        if overwrite:
            profile.birth_city = city[:255] or None
        elif city and not profile.birth_city:
            profile.birth_city = city[:255]

    if birth_time is not None:
        clock = birth_time.strip()
        if overwrite:
            profile.birth_time = clock[:128] or None
        elif clock and not profile.birth_time:
            profile.birth_time = clock[:128]

    await session.flush()
    return profile


def serialize_profile(profile: SoulProfile | None, user: User, ident: WebIdentity | None) -> dict:
    name = (profile.name if profile else None) or (ident.name if ident else None) or user.first_name
    return {
        "name": name or "",
        "birth_date": _fmt_birth(profile.birth_date if profile else None),
        "birth_city": (profile.birth_city if profile else None) or "",
        "birth_time": (profile.birth_time if profile else None) or "",
    }


async def backfill_profile_from_readings(session: AsyncSession, user: User) -> SoulProfile:
    profile = await upsert_soul_profile(session, user)
    if profile.birth_date and profile.birth_city:
        return profile
    webs = list((await session.scalars(select(WebSession).where(WebSession.user_id == user.id))).all())
    if not webs:
        return profile
    rows = (
        await session.scalars(
            select(WebReading)
            .where(WebReading.session_id.in_([row.id for row in webs]))
            .order_by(WebReading.created_at.desc())
        )
    ).all()
    for row in rows:
        payload = row.input_payload or {}
        await upsert_soul_profile(
            session,
            user,
            birth=payload.get("birth"),
            birth_city=payload.get("birth_city"),
            birth_time=payload.get("birth_time"),
            overwrite=False,
        )
        profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id)) or profile
        if profile.birth_date and profile.birth_city:
            break
    return profile


def _card_image_url(path: str | None) -> str | None:
    if not path:
        return None
    name = Path(path).name
    return f"/static/tarot_cards/{name}"


async def resolved_cards(session: AsyncSession) -> dict[str, WebCard]:
    rows = await session.execute(select(WebCardOverride))
    overrides = {row.card_id: row.payload for row in rows.scalars()}
    out: dict[str, WebCard] = {}
    for card_id, card in CARDS.items():
        payload = overrides.get(card_id) or {}
        out[card_id] = apply_override(card, payload) if payload else card
    return out


async def public_catalog(session: AsyncSession) -> list[dict]:
    cards = await resolved_cards(session)
    return [public_card(card) for card in cards.values()]


async def ensure_session(
    session: AsyncSession,
    guest_id: str,
    *,
    utm: dict | None = None,
    metrika_client_id: str | None = None,
    user: User | None = None,
) -> WebSession:
    row = await session.scalar(select(WebSession).where(WebSession.guest_id == guest_id))
    if row is None:
        row = WebSession(guest_id=guest_id, utm=utm or {}, metrika_client_id=metrika_client_id)
        session.add(row)
        await session.flush()
    if utm:
        merged = dict(row.utm or {})
        for key, value in utm.items():
            if value and not merged.get(key):
                merged[key] = value
        row.utm = merged
    if metrika_client_id and not row.metrika_client_id:
        row.metrika_client_id = metrika_client_id
    if user:
        row.user_id = user.id
    return row


def guest_telegram_id(guest_id: str) -> int:
    digest = hashlib.sha256(guest_id.encode("utf-8")).hexdigest()
    return -int(digest[:12], 16)


async def ensure_guest_user(session: AsyncSession, web: WebSession) -> User:
    if web.user_id:
        user = await session.scalar(select(User).where(User.id == web.user_id))
        if user:
            return user
    tid = guest_telegram_id(web.guest_id)
    user = await session.scalar(select(User).where(User.telegram_id == tid))
    if user is None:
        try:
            async with session.begin_nested():
                user = User(telegram_id=tid, first_name="Гость сайта", language_code="ru")
                session.add(user)
                await session.flush()
        except IntegrityError:
            user = await session.scalar(select(User).where(User.telegram_id == tid))
            if user is None:
                raise
    web.user_id = user.id
    return user


async def random_deck(session: AsyncSession, n: int = 7) -> list[dict]:
    rows = list((await session.scalars(select(TarotCard).where(TarotCard.arcana == "major"))).all())
    if len(rows) < n:
        rows = list((await session.scalars(select(TarotCard))).all())
    rows = list(rows)
    secrets.SystemRandom().shuffle(rows)
    picked = rows[:n]
    return [
        {
            "slug": card.slug,
            "back": True,
            "image": _card_image_url(card.image_path),
        }
        for card in picked
    ]


async def _load_drawn(session: AsyncSession, slugs: list[str]) -> list[dict]:
    if not slugs:
        return []
    rows = list((await session.scalars(select(TarotCard).where(TarotCard.slug.in_(slugs)))).all())
    by_slug = {row.slug: row for row in rows}
    drawn = []
    for slug in slugs:
        row = by_slug.get(slug)
        if not row:
            continue
        drawn.append(
            {
                "slug": row.slug,
                "name": row.name,
                "description": row.description,
                "image": _card_image_url(row.image_path),
            }
        )
    return drawn


def _topic_blocked(answers: list[str]) -> bool:
    blob = " ".join(answers).lower()
    return any(word in blob for word in BANNED)


async def create_reading(
    session: AsyncSession,
    *,
    guest_id: str,
    card_id: str,
    answers: list[str],
    slugs: list[str] | None = None,
    birth: str | None = None,
    birth_city: str | None = None,
    birth_time: str | None = None,
    partner_birth: str | None = None,
    utm: dict | None = None,
    metrika_client_id: str | None = None,
    user: User | None = None,
) -> WebReading:
    if _topic_blocked(answers):
        raise ValueError("Эта тема закрыта. Выбери соседний вопрос — про чувства, деньги или работу.")
    cards = await resolved_cards(session)
    card = cards.get(card_id)
    if card is None:
        raise ValueError("Неизвестная карточка")
    web = await ensure_session(
        session, guest_id, utm=utm, metrika_client_id=metrika_client_id, user=user
    )
    birth_d = _parse_date(birth)
    partner_d = _parse_date(partner_birth)
    if card.branch in {"date", "pair"} and birth_d is None:
        raise ValueError("Нужна дата рождения")
    if card.branch == "pair" and partner_d is None:
        raise ValueError("Нужна вторая дата")
    drawn = await _load_drawn(session, slugs or [])
    if card.branch == "taro" and len(drawn) < card.cards_n:
        raise ValueError("Выбери карты")

    cache_payload = None
    if card.branch in {"date", "pair"} and birth_d:
        cache_key = f"{card.sku}:{birth_d.isoformat()}:{partner_d.isoformat() if partner_d else ''}"
        cached = await session.scalar(select(WebMatrixCache).where(WebMatrixCache.cache_key == cache_key))
        if cached:
            cache_payload = cached.payload

    mini = cache_payload.get("mini") if cache_payload else None
    if not mini:
        mini = build_mini(card, answers, drawn=drawn, birth=birth_d, partner_birth=partner_d)
        if card.branch in {"date", "pair"} and birth_d and not cache_payload:
            session.add(
                WebMatrixCache(
                    cache_key=f"{card.sku}:{birth_d.isoformat()}:{partner_d.isoformat() if partner_d else ''}",
                    payload={"mini": mini},
                )
            )

    token = secrets.token_urlsafe(16)
    reading = WebReading(
        token=token,
        session_id=web.id,
        card_id=card.id,
        branch=card.branch,
        sku=card.sku,
        status="ready" if card.price_rub == 0 else "mini",
        answers=answers,
        input_payload={
            "slugs": slugs or [],
            "birth": birth,
            "birth_city": birth_city,
            "birth_time": birth_time,
            "partner_birth": partner_birth,
            "drawn": drawn,
            "price_rub": card.price_rub,
            "product_name": card.product_name,
            "context": card.context,
            "includes": list(card.positions or card.open_blocks) + list(card.closed_blocks),
        },
        mini=mini,
        paid_text=None if card.price_rub else _free_full_text(mini),
        expires_at=datetime.now(UTC) + READING_TTL,
    )
    session.add(reading)
    await session.flush()
    owner = user or await ensure_guest_user(session, web)
    await upsert_soul_profile(
        session,
        owner,
        birth=birth,
        birth_city=birth_city,
        birth_time=birth_time,
        overwrite=True,
    )
    return reading


def _free_full_text(mini: dict) -> str:
    parts = [mini.get("mirror") or ""]
    for block in mini.get("blocks") or []:
        parts.append(str(block.get("text") or ""))
    parts.append(mini.get("cut") or "")
    return "\n\n".join(p for p in parts if p)


def _offer_meta(reading: WebReading) -> tuple[list[str], str]:
    from app.services.web.catalog import CARDS

    raw = reading.input_payload or {}
    includes = [str(item) for item in (raw.get("includes") or []) if item]
    context = str(raw.get("context") or "")
    card = CARDS.get(reading.card_id)
    if card:
        if not includes:
            includes = list(card.positions or card.open_blocks) + list(card.closed_blocks)
        if not context:
            context = card.context
    return includes, context


def public_reading(reading: WebReading, *, include_paid: bool = False) -> dict:
    paid = bool(reading.status in {"paid", "ready"} and reading.paid_text)
    includes, context = _offer_meta(reading)
    payload = {
        "token": reading.token,
        "card_id": reading.card_id,
        "branch": reading.branch,
        "sku": reading.sku,
        "status": reading.status,
        "mini": reading.mini,
        "price_rub": int((reading.input_payload or {}).get("price_rub") or 0),
        "product_name": (reading.input_payload or {}).get("product_name"),
        "drawn": (reading.input_payload or {}).get("drawn") or [],
        "includes": includes,
        "context": context,
        "paid": paid,
        "can_pay": (not paid) and int((reading.input_payload or {}).get("price_rub") or 0) > 0,
        "source": "web",
        "created_at": reading.created_at.isoformat() if reading.created_at else None,
        "expires_at": reading.expires_at.isoformat() if reading.expires_at else None,
    }
    if include_paid and paid:
        payload["paid_text"] = reading.paid_text
    return payload


async def _pending_by_key(session: AsyncSession, user_id: str, key: str) -> Payment | None:
    rows = list(
        (
            await session.scalars(
                select(Payment)
                .where(Payment.user_id == user_id, Payment.status == "pending")
                .order_by(Payment.created_at.desc())
                .limit(30)
            )
        ).all()
    )
    for row in rows:
        if (row.payload or {}).get("idempotency_key") == key:
            return row
    return None


def _payment_result(payment: Payment, *, token: str | None = None) -> dict:
    if payment.provider == "demo" and payment.status == "completed":
        out = {"ok": True, "demo": True}
    elif (payment.payload or {}).get("payment_url"):
        out = {"ok": True, "payment_url": payment.payload["payment_url"], "reused": True}
    else:
        out = {"ok": True}
    if token:
        out["token"] = token
    return out


async def _open_robokassa(
    session: AsyncSession,
    payment: Payment,
    *,
    amount: Decimal,
    title: str,
    success_url: str,
    fail_url: str,
) -> dict:
    settings = get_settings()
    if not settings.robokassa_configured:
        if not settings.payments_demo_mode:
            raise ValueError("Оплата временно недоступна")
        payment.provider = "demo"
        payment.provider_payment_id = f"demo_{payment.id}"
        from app.services.billing.service import BillingService

        await BillingService().complete_payment(session, payment)
        return _payment_result(payment, token=(payment.payload or {}).get("token"))
    if payment.provider_payment_id and (payment.payload or {}).get("payment_url"):
        return _payment_result(payment, token=(payment.payload or {}).get("token"))
    inv_id = await next_invoice_id()
    try:
        url = build_payment_url(
            payment_id=str(payment.id),
            inv_id=inv_id,
            amount_rub=amount,
            description=f"Лея · {title}"[:100],
            success_url=success_url,
            fail_url=fail_url,
        )
    except RobokassaNotConfiguredError as exc:
        raise ValueError("Оплата временно недоступна") from exc
    payment.provider_payment_id = str(inv_id)
    payload = dict(payment.payload or {})
    payload["payment_url"] = url
    payload["inv_id"] = str(inv_id)
    payment.payload = payload
    return {"ok": True, "payment_url": url, "token": payload.get("token")}


async def checkout(
    session: AsyncSession,
    reading: WebReading,
    *,
    tariff: str,
    recur_consent: bool = False,
    email: str | None = None,
    marketing: bool = False,
    privacy: bool = False,
) -> dict:
    if email and email.strip():
        await save_contact(
            session,
            reading,
            email=email,
            telegram=None,
            marketing=marketing,
            privacy=privacy,
        )
    cards = await resolved_cards(session)
    card = cards[reading.card_id]
    web = await session.scalar(select(WebSession).where(WebSession.id == reading.session_id))
    if web is None:
        raise ValueError("Сессия не найдена")
    user = await ensure_guest_user(session, web)

    if tariff != "test" and web.unlimited_until and web.unlimited_until > datetime.now(UTC):
        await fulfill_paid(session, reading)
        return {"ok": True, "unlimited": True, "token": reading.token}

    base = int(card.price_rub)
    bind_reading = True
    if tariff == "test":
        from app.services.products.packages import TEST_PAYMENT_ENABLED

        if not TEST_PAYMENT_ENABLED:
            raise ValueError("Тестовый платёж выключен")
        amount = Decimal("10")
        sku = "test_10"
        title = "Тестовый платёж 10 ₽"
        bind_reading = False
    elif tariff == "bundle":
        amount = Decimal(base + 300)
        sku = f"{card.sku}_bundle"
        title = f"{card.product_name} + доп. разбор"
    elif tariff == "unlimited":
        if not recur_consent:
            raise ValueError("Нужно согласие на подписку")
        amount = Decimal("590")
        sku = "web_unlimited_month"
        title = "Безлимит на месяц"
    elif tariff == "upsell":
        amount = Decimal("690") if card.branch == "taro" else Decimal("390")
        sku = "web_upsell"
        title = "Апселл"
    else:
        amount = Decimal(base)
        sku = card.sku
        title = card.product_name
    if amount <= 0:
        await fulfill_paid(session, reading)
        return {"ok": True, "token": reading.token}

    if reading.status in {"paid", "ready"} and tariff in {"base", "bundle"}:
        return {"ok": True, "token": reading.token}

    if tariff == "test":
        purpose = "test_payment"
        key = f"web_test:{user.id}:{reading.id}"
    elif sku == "web_unlimited_month":
        purpose = "web_unlimited"
        key = f"web_reading:{reading.id}:{tariff}"
    else:
        purpose = "web_reading"
        key = f"web_reading:{reading.id}:{tariff}"
    settings = get_settings()
    success_url = f"{settings.public_base_url.rstrip('/')}/r/{reading.token}"
    if tariff == "test":
        success_url = f"{success_url}?pay=test"
    fail_url = f"{settings.public_base_url.rstrip('/')}/r/{reading.token}?pay=fail"

    payment = None
    if bind_reading and reading.payment_id:
        existing = await session.scalar(select(Payment).where(Payment.id == reading.payment_id))
        if (
            existing
            and existing.status == "pending"
            and existing.amount_rub == amount
            and (existing.payload or {}).get("tariff") == tariff
        ):
            payment = existing
    if payment is None:
        payment = await _pending_by_key(session, user.id, key)
    if payment is not None:
        if bind_reading:
            reading.payment_id = payment.id
        payload = dict(payment.payload or {})
        payload["idempotency_key"] = key
        payload["token"] = reading.token
        payload["sku"] = sku
        payload["tariff"] = tariff
        payload["reading_id"] = reading.id
        payload["metrika_client_id"] = web.metrika_client_id
        payload["yclid"] = (web.utm or {}).get("yclid")
        payment.payload = payload
        result = await _open_robokassa(
            session, payment, amount=amount, title=title, success_url=success_url, fail_url=fail_url
        )
        result["token"] = reading.token
        return result

    payment = Payment(
        user_id=user.id,
        provider="robokassa",
        purpose=purpose,
        amount_rub=amount,
        status="pending",
        payload={
            "reading_id": reading.id,
            "token": reading.token,
            "sku": sku,
            "tariff": tariff,
            "idempotency_key": key,
            "metrika_client_id": web.metrika_client_id,
            "yclid": (web.utm or {}).get("yclid"),
        },
    )
    session.add(payment)
    await session.flush()
    if bind_reading:
        reading.payment_id = payment.id
    result = await _open_robokassa(
        session, payment, amount=amount, title=title, success_url=success_url, fail_url=fail_url
    )
    result["token"] = reading.token
    return result


async def fulfill_paid(session: AsyncSession, reading: WebReading) -> None:
    if reading.paid_text and reading.status in {"paid", "ready"}:
        return
    cards = await resolved_cards(session)
    card = cards.get(reading.card_id)
    if card is None:
        return
    drawn = (reading.input_payload or {}).get("drawn") or []
    answers = reading.answers or []
    cards_txt = ", ".join(f"{item.get('name')}" for item in drawn) or "—"
    prompt = (
        "Ты Лея. Пиши на «ты», без жаргона арканов в ветке дат, без гарантий. "
        "Не отвечай всегда «да» на «вернётся ли он». "
        "Запрещены здоровье, беременность, диагнозы, смерть, суицид, юриспруденция. "
        "Это разбор с сайта, не выдавай себя за живого таролога.\n\n"
        f"Карточка: {card.title}\n"
        f"Продукт: {card.product_name}\n"
        f"Ответы квиза: {answers}\n"
        f"Карты: {cards_txt}\n"
        f"Дата: {(reading.input_payload or {}).get('birth')}\n"
        f"Партнёр: {(reading.input_payload or {}).get('partner_birth')}\n\n"
        "Дай полный разбор 8–12 абзацев. В конце — одно конкретное действие на неделю."
    )
    try:
        text = await KieClient().chat_completion(
            [{"role": "user", "content": prompt}],
            reasoning_effort="low",
        )
    except Exception:
        logger.exception("web paid generation failed token=%s", reading.token)
        text = _free_full_text(reading.mini or {})
        text += "\n\nПолный разбор допишется, когда модель ответит. Ссылка уже твоя."
    reading.paid_text = text
    reading.status = "paid"
    await session.flush()


async def save_contact(
    session: AsyncSession,
    reading: WebReading,
    *,
    email: str | None,
    telegram: str | None,
    marketing: bool,
    privacy: bool,
) -> None:
    web = await session.scalar(select(WebSession).where(WebSession.id == reading.session_id))
    if web is None:
        return
    if email:
        web.email = email.strip().lower()[:255]
    if telegram:
        web.telegram = telegram.strip()[:255]
    web.marketing_opt_in = bool(marketing)
    web.privacy_opt_in = bool(privacy)
    if web.email:
        from app.services.web.mailer import send_reading_link

        send_reading_link(web.email, reading.token)


async def checkout_package(session: AsyncSession, user: User, package_id: str) -> dict:
    from app.services.products.packages import PACKAGES

    pkg = PACKAGES.get(package_id)
    if pkg is None:
        raise ValueError("Нет такого пакета")
    settings = get_settings()
    key = f"web_pkg:{user.id}:{pkg.id}"
    success_url = f"{settings.public_base_url.rstrip('/')}/lk"
    fail_url = f"{settings.public_base_url.rstrip('/')}/lk?pay=fail"
    payment = await _pending_by_key(session, user.id, key)
    if payment is None:
        payment = Payment(
            user_id=user.id,
            provider="robokassa",
            purpose=pkg.purpose,
            amount_rub=pkg.price_rub,
            status="pending",
            payload={"package_id": pkg.id, "title": pkg.title, "idempotency_key": key},
        )
        session.add(payment)
        await session.flush()
    return await _open_robokassa(
        session,
        payment,
        amount=pkg.price_rub,
        title=pkg.title,
        success_url=success_url,
        fail_url=fail_url,
    )


def _product_label(product_id: str) -> str:
    from app.services.products.catalog import PRODUCTS

    product = PRODUCTS.get(product_id)
    if product:
        return f"{product.emoji} {product.title}"
    return product_id


def _inject_system_addon(messages: list[dict], addon: str) -> list[dict]:
    if not messages or messages[0].get("role") != "system":
        return [{"role": "system", "content": [{"type": "text", "text": addon}]}] + messages
    updated = list(messages)
    first = dict(updated[0])
    content = first.get("content") or []
    if content and isinstance(content[0], dict):
        text = content[0].get("text", "")
        first["content"] = [{"type": "text", "text": f"{text}\n\n{addon}"}]
    elif isinstance(content, str):
        first["content"] = f"{content}\n\n{addon}"
    updated[0] = first
    return updated


def serialize_chat_message(row: Message) -> dict:
    from app.bot.formatting import leia_markdown_to_web_html

    meta = row.meta or {}
    text = row.content or ""
    if meta.get("source") == "product_reading":
        title = meta.get("product_title") or "Разбор"
        text = f"{title}\n\n{text}"
    if len(text) > 4000:
        text = text[:4000] + "…"
    role = "user" if row.role == MessageRole.USER.value else "leia"
    return {
        "id": row.id,
        "role": role,
        "text": text,
        "html": leia_markdown_to_web_html(text) if role == "leia" else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def load_chat_history(session: AsyncSession, user: User, *, limit: int = 80) -> list[dict]:
    rows = list(
        (
            await session.scalars(
                select(Message)
                .where(Message.user_id == user.id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
    rows.reverse()
    out = []
    for row in rows:
        if (row.meta or {}).get("source") == "product_reading":
            continue
        if (row.meta or {}).get("thread") == "reading":
            continue
        out.append(serialize_chat_message(row))
    return out


async def load_reading_thread(session: AsyncSession, user: User, reading_token: str) -> list[dict]:
    rows = list(
        (
            await session.scalars(
                select(Message)
                .where(Message.user_id == user.id)
                .order_by(Message.created_at.desc())
                .limit(80)
            )
        ).all()
    )
    rows.reverse()
    out = []
    for row in rows:
        meta = row.meta or {}
        if meta.get("thread") != "reading" or meta.get("reading_token") != reading_token:
            continue
        out.append(serialize_chat_message(row))
    return out


async def _count_reading_user_msgs(session: AsyncSession, user_id: str, reading_token: str) -> int:
    rows = list(
        (
            await session.scalars(
                select(Message).where(
                    Message.user_id == user_id,
                    Message.role == MessageRole.USER.value,
                )
            )
        ).all()
    )
    return sum(
        1
        for row in rows
        if (row.meta or {}).get("thread") == "reading"
        and (row.meta or {}).get("reading_token") == reading_token
    )


async def _has_paid_plan(user_id: str) -> bool:
    from app.services.products.entitlements import EntitlementService

    ent = EntitlementService()
    return bool(await ent.has_any_plan(user_id))


async def _has_web_unlimited(session: AsyncSession, user_id: str) -> bool:
    now = datetime.now(UTC)
    rows = list((await session.scalars(select(WebSession).where(WebSession.user_id == user_id))).all())
    return any(bool(row.unlimited_until and row.unlimited_until > now) for row in rows)


async def _can_discuss_readings(session: AsyncSession, user_id: str) -> bool:
    return await _has_paid_plan(user_id) or await _has_web_unlimited(session, user_id)


def _reading_item_can_pay(item: dict) -> bool:
    if item.get("source") == "telegram":
        return False
    if item.get("paid"):
        return False
    return bool(item.get("can_pay") or (item.get("price_rub") or 0) > 0)


async def cabinet_payload(session: AsyncSession, user: User) -> dict:
    from app.services.products.entitlements import EntitlementService
    from app.services.products.packages import PACKAGES

    ident = await session.scalar(select(WebIdentity).where(WebIdentity.user_id == user.id))
    profile = await backfill_profile_from_readings(session, user)
    webs = list((await session.scalars(select(WebSession).where(WebSession.user_id == user.id))).all())
    web_ids = [row.id for row in webs]
    readings = []
    if web_ids:
        rows = (
            await session.scalars(
                select(WebReading)
                .where(WebReading.session_id.in_(web_ids))
                .order_by(WebReading.created_at.desc())
            )
        ).all()
        readings = []
        for row in rows:
            item = public_reading(row, include_paid=True)
            if not item.get("paid_text"):
                item["paid_text"] = _free_full_text(row.mini or {})
            readings.append(item)
    tg_rows = list(
        (
            await session.scalars(
                select(TarotReading)
                .where(TarotReading.user_id == user.id)
                .order_by(TarotReading.created_at.desc())
                .limit(40)
            )
        ).all()
    )
    for row in tg_rows:
        readings.append(
            {
                "token": f"tg:{row.id}",
                "card_id": row.reading_type,
                "product_name": row.reading_type,
                "paid": True,
                "source": "telegram",
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "mini": {
                    "title": row.reading_type,
                    "lead": (row.question or "")[:240],
                },
                "paid_text": row.interpretation,
            }
        )
    usage_rows = list(
        (
            await session.scalars(
                select(ProductUsage)
                .where(
                    ProductUsage.user_id == user.id,
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
                .order_by(ProductUsage.created_at.desc())
                .limit(50)
            )
        ).all()
    )
    for row in usage_rows:
        title = _product_label(row.product_id)
        readings.append(
            {
                "token": f"pu:{row.id}",
                "card_id": row.product_id,
                "product_name": title,
                "paid": row.level == "full",
                "source": "telegram",
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "mini": {
                    "title": title,
                    "lead": "полная" if row.level == "full" else "мини",
                },
                "paid_text": row.content_preview,
            }
        )
    seen_usage = {row.id for row in usage_rows}
    product_msgs = list(
        (
            await session.scalars(
                select(Message)
                .where(Message.user_id == user.id, Message.role == MessageRole.ASSISTANT.value)
                .order_by(Message.created_at.desc())
                .limit(120)
            )
        ).all()
    )
    for msg in product_msgs:
        meta = msg.meta or {}
        if meta.get("source") != "product_reading":
            continue
        usage_id = str(meta.get("product_usage_id") or "")
        if usage_id and usage_id in seen_usage:
            continue
        if usage_id:
            seen_usage.add(usage_id)
        title = meta.get("product_title") or _product_label(str(meta.get("product_id") or "telegram"))
        readings.append(
            {
                "token": f"pu:{usage_id}" if usage_id else f"msg:{msg.id}",
                "card_id": str(meta.get("product_id") or "telegram"),
                "product_name": title,
                "paid": meta.get("level") == "full",
                "source": "telegram",
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "mini": {
                    "title": title,
                    "lead": meta.get("level_label") or "",
                },
                "paid_text": msg.content,
            }
        )
    readings.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    from app.bot.formatting import leia_markdown_to_web_html

    plan = await _can_discuss_readings(session, user.id)
    for item in readings:
        body = item.get("paid_text") or (item.get("mini") or {}).get("lead") or ""
        item["html"] = leia_markdown_to_web_html(body)
        token = str(item.get("token") or "")
        paid = bool(item.get("paid"))
        item["can_pay"] = _reading_item_can_pay(item)
        item["can_chat"] = bool(paid or plan)
        if item["can_chat"] and token:
            used = await _count_reading_user_msgs(session, user.id, token)
            item["chat_left"] = max(0, READING_CHAT_LIMIT - used)
        else:
            item["chat_left"] = 0
    ent = EntitlementService()
    snap = await ent.cabinet_snapshot(user.id)
    return {
        "user": {
            "id": user.id,
            "name": serialize_profile(profile, user, ident)["name"],
            "email": ident.email if ident else None,
            "telegram_bound": bool(user.telegram_id and user.telegram_id > 0),
            "telegram_username": user.username,
        },
        "profile": serialize_profile(profile, user, ident),
        "plan": snap["plan"],
        "vip": snap["vip"],
        "love_plus": snap["love_plus"],
        "subscription": snap["subscription"],
        "active_packages": snap["active_packages"],
        "readings": readings,
        "chat": await load_chat_history(session, user),
        "packages": [
            {
                "id": pkg.id,
                "title": pkg.title,
                "emoji": pkg.emoji,
                "price_rub": int(pkg.price_rub),
                "pitch": pkg.pitch,
            }
            for pkg in PACKAGES.values()
        ],
    }


async def chat_reply(
    session: AsyncSession,
    user: User,
    *,
    text: str,
    reading_token: str | None,
) -> dict:
    from app.services.ai.context import ContextBuilder
    from app.services.billing.service import BillingService
    from app.services.memory.extractor import MemoryExtractor
    from app.services.products.entitlements import EntitlementService

    text = (text or "").strip()
    if len(text) < 2:
        raise ValueError("Напиши сообщение")
    if len(text) > 4000:
        raise ValueError("Слишком длинно")

    reading = None
    tg_reading = None
    product_usage = None
    product_snippet = None
    if reading_token:
        if reading_token.startswith("tg:"):
            tg_reading = await session.scalar(
                select(TarotReading).where(
                    TarotReading.id == reading_token[3:],
                    TarotReading.user_id == user.id,
                )
            )
            if tg_reading is None:
                raise ValueError("Разбор не найден")
        elif reading_token.startswith("pu:"):
            product_usage = await session.scalar(
                select(ProductUsage).where(
                    ProductUsage.id == reading_token[3:],
                    ProductUsage.user_id == user.id,
                )
            )
            if product_usage is None:
                for msg in (
                    await session.scalars(
                        select(Message)
                        .where(Message.user_id == user.id)
                        .order_by(Message.created_at.desc())
                        .limit(120)
                    )
                ).all():
                    if str((msg.meta or {}).get("product_usage_id") or "") == reading_token[3:]:
                        meta = msg.meta or {}
                        product_snippet = (
                            str(meta.get("product_title") or _product_label(str(meta.get("product_id") or "telegram"))),
                            msg.content or "",
                        )
                        break
                if product_snippet is None:
                    raise ValueError("Разбор не найден")
        elif reading_token.startswith("msg:"):
            product_msg = await session.scalar(
                select(Message).where(Message.id == reading_token[4:], Message.user_id == user.id)
            )
            if product_msg is None:
                raise ValueError("Разбор не найден")
            meta = product_msg.meta or {}
            product_snippet = (
                str(meta.get("product_title") or _product_label(str(meta.get("product_id") or "telegram"))),
                product_msg.content or "",
            )
        else:
            reading = await session.scalar(select(WebReading).where(WebReading.token == reading_token))
            if reading is None:
                raise ValueError("Разбор не найден")

    plan = await _can_discuss_readings(session, user.id)
    vip = await EntitlementService().has_vip(user.id)
    bound = bool(user.telegram_id and user.telegram_id > 0)
    paid = bool(
        (reading and reading.status in {"paid", "ready"} and reading.paid_text)
        or tg_reading
        or (product_usage and product_usage.level == "full" and product_usage.content_preview)
        or product_snippet
        or (product_usage and product_usage.content_preview and plan)
    )
    reading_thread = bool(reading_token)
    if reading_thread:
        if not paid and not plan:
            raise ValueError("Сначала оплати полный разбор — потом можно спросить Лею про него.")
        used = await _count_reading_user_msgs(session, user.id, reading_token)
        if used >= READING_CHAT_LIMIT:
            raise ValueError(f"По этому разбору уже {READING_CHAT_LIMIT} сообщений. Новый вопрос — новый разбор или пакет.")
    elif not bound and not vip:
        raise ValueError("Свободный чат — с VIP или после привязки Telegram. По оплаченному разбору — кнопка «Обсудить».")

    messages = await ContextBuilder().build(session, user, user_query=text, channel="web")
    if reading_thread:
        messages = [m for m in messages if m.get("role") == "system"]
        messages = _inject_system_addon(
            messages,
            "Сейчас человек пишет с сайта в отдельном чате по одному разбору. "
            "Держись контекста этого разбора и профиля пользователя. "
            "Не уходи в новый расклад и не предлагай заново гадать, если не спросили. "
            "Коротко, на «ты», как Лея.",
        )
    else:
        messages = _inject_system_addon(
            messages,
            "Сейчас пишут с сайта. Ты та же Лея, что в Telegram. Не начинай диалог с нуля.",
        )
    addon_parts = []
    if reading:
        addon_parts.append(
            f"Открыт разбор сайта «{reading.card_id}». Мини: {json.dumps(reading.mini, ensure_ascii=False)[:2500]}"
        )
        if reading.paid_text:
            addon_parts.append(f"Полный текст:\n{(reading.paid_text or '')[:5000]}")
    if tg_reading:
        addon_parts.append(
            f"Открыт разбор из Telegram «{tg_reading.reading_type}». "
            f"Вопрос: {(tg_reading.question or '')[:800]}\nТекст:\n{(tg_reading.interpretation or '')[:5000]}"
        )
    if product_usage:
        addon_parts.append(
            f"Открыт разбор из Telegram «{_product_label(product_usage.product_id)}» "
            f"({'полная' if product_usage.level == 'full' else 'мини'}).\n"
            f"{(product_usage.content_preview or '')[:5000]}"
        )
    if product_snippet:
        addon_parts.append(f"Открыт разбор из Telegram «{product_snippet[0]}».\n{product_snippet[1][:5000]}")
    if reading_thread:
        profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
        ident = await session.scalar(select(WebIdentity).where(WebIdentity.user_id == user.id))
        name = (profile.name if profile else None) or user.first_name or (ident.name if ident else "") or ""
        birth = profile.birth_date.isoformat() if profile and profile.birth_date else ""
        city = (profile.birth_city if profile else "") or ""
        addon_parts.append(
            f"Пользователь: {name or 'без имени'}"
            + (f", дата рождения {birth}" if birth else "")
            + (f", город {city}" if city else "")
            + ". Отвечай лично, с опорой на этот разбор, не как в общем чате."
        )
    if addon_parts:
        messages = _inject_system_addon(messages, "\n".join(addon_parts))
    if reading_thread and reading_token:
        for row in await load_reading_thread(session, user, reading_token):
            role = "user" if row.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": [{"type": "text", "text": row.get("text") or ""}]})
    messages.append({"role": "user", "content": [{"type": "text", "text": text}]})

    billing = BillingService()
    billing_mode = "web_reading" if reading_thread else "web"
    if not reading_thread and (bound or vip):
        allowed, reason, billing_mode = await billing.ensure_can_use_chat(
            session, user, context_messages=messages
        )
        if not allowed and not vip:
            raise ValueError(reason)
        if allowed:
            billing_mode = await billing.reserve_chat_slot(session, user, billing_mode)

    reply = await KieClient().chat_completion(messages, reasoning_effort="low")
    meta = {
        "channel": "web",
        "reading_token": reading_token,
        "billing_mode": billing_mode,
    }
    if reading_thread:
        meta["thread"] = "reading"
    session.add(Message(user_id=user.id, role=MessageRole.USER.value, content=text, meta=meta))
    session.add(Message(user_id=user.id, role=MessageRole.ASSISTANT.value, content=reply, meta=meta))
    await session.flush()
    try:
        await MemoryExtractor().extract_from_dialog(session, user, text, reply)
    except Exception:
        logger.exception("web chat memory extract failed")
    await session.flush()
    if reading_thread and reading_token:
        used = await _count_reading_user_msgs(session, user.id, reading_token)
        return {
            "reply": reply,
            "chat": await load_reading_thread(session, user, reading_token),
            "chat_left": max(0, READING_CHAT_LIMIT - used),
        }
    return {"reply": reply, "chat": await load_chat_history(session, user)}

