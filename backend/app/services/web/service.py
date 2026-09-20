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
    Payment,
    TarotCard,
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
BANNED = ("суицид", "беремен", "диагноз", "смерть", "юридическ", "лечение", "аборт")


def _parse_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


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
) -> WebSession:
    row = await session.scalar(select(WebSession).where(WebSession.guest_id == guest_id))
    if row is None:
        row = WebSession(guest_id=guest_id, utm=utm or {}, metrika_client_id=metrika_client_id)
        session.add(row)
        await session.flush()
        return row
    if utm:
        merged = dict(row.utm or {})
        merged.update({k: v for k, v in utm.items() if v})
        row.utm = merged
    if metrika_client_id:
        row.metrika_client_id = metrika_client_id
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
) -> WebReading:
    if _topic_blocked(answers):
        raise ValueError("Эта тема закрыта. Выбери соседний вопрос — про чувства, деньги или работу.")
    cards = await resolved_cards(session)
    card = cards.get(card_id)
    if card is None:
        raise ValueError("Неизвестная карточка")
    web = await ensure_session(session, guest_id, utm=utm, metrika_client_id=metrika_client_id)
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
        },
        mini=mini,
        paid_text=None if card.price_rub else _free_full_text(mini),
        expires_at=datetime.now(UTC) + READING_TTL,
    )
    session.add(reading)
    await session.flush()
    return reading


def _free_full_text(mini: dict) -> str:
    parts = [mini.get("mirror") or ""]
    for block in mini.get("blocks") or []:
        parts.append(str(block.get("text") or ""))
    parts.append(mini.get("cut") or "")
    return "\n\n".join(p for p in parts if p)


def public_reading(reading: WebReading, *, include_paid: bool = False) -> dict:
    paid = bool(reading.status in {"paid", "ready"} and reading.paid_text)
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
        "paid": paid,
        "expires_at": reading.expires_at.isoformat() if reading.expires_at else None,
    }
    if include_paid and paid:
        payload["paid_text"] = reading.paid_text
    return payload


async def checkout(
    session: AsyncSession,
    reading: WebReading,
    *,
    tariff: str,
    recur_consent: bool = False,
) -> dict:
    cards = await resolved_cards(session)
    card = cards[reading.card_id]
    web = await session.scalar(select(WebSession).where(WebSession.id == reading.session_id))
    if web is None:
        raise ValueError("Сессия не найдена")
    user = await ensure_guest_user(session, web)

    if web.unlimited_until and web.unlimited_until > datetime.now(UTC):
        await fulfill_paid(session, reading)
        return {"ok": True, "unlimited": True, "token": reading.token}

    base = int(card.price_rub)
    if tariff == "bundle":
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

    purpose = "web_unlimited" if sku == "web_unlimited_month" else "web_reading"
    payment = Payment(
        user_id=user.id,
        provider="robokassa",
        purpose=purpose,
        amount_rub=amount,
        status="pending",
        payload={"reading_id": reading.id, "token": reading.token, "sku": sku, "tariff": tariff},
    )
    session.add(payment)
    await session.flush()
    reading.payment_id = payment.id
    settings = get_settings()
    if not settings.robokassa_configured:
        if not settings.payments_demo_mode:
            raise ValueError("Оплата временно недоступна")
        payment.provider = "demo"
        payment.provider_payment_id = f"demo_{payment.id}"
        from app.services.billing.service import BillingService

        await BillingService().complete_payment(session, payment)
        return {"ok": True, "demo": True, "token": reading.token}

    inv_id = await next_invoice_id()
    try:
        url = build_payment_url(
            payment_id=str(payment.id),
            inv_id=inv_id,
            amount_rub=amount,
            description=f"Лея · {title}"[:100],
            success_url=f"{settings.public_base_url.rstrip('/')}/r/{reading.token}",
            fail_url=f"{settings.public_base_url.rstrip('/')}/r/{reading.token}?pay=fail",
        )
    except RobokassaNotConfiguredError:
        raise ValueError("Оплата временно недоступна")
    payment.provider_payment_id = str(inv_id)
    payload = dict(payment.payload or {})
    payload["payment_url"] = url
    payload["inv_id"] = str(inv_id)
    payment.payload = payload
    return {"ok": True, "payment_url": url, "token": reading.token}


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
    from app.services.billing.service import BillingService

    pkg = PACKAGES.get(package_id)
    if pkg is None:
        raise ValueError("Нет такого пакета")
    payment = Payment(
        user_id=user.id,
        provider="robokassa",
        purpose=pkg.purpose,
        amount_rub=pkg.price_rub,
        status="pending",
        payload={"package_id": pkg.id, "title": pkg.title},
    )
    session.add(payment)
    await session.flush()
    settings = get_settings()
    if not settings.robokassa_configured:
        if not settings.payments_demo_mode:
            raise ValueError("Оплата временно недоступна")
        payment.provider = "demo"
        payment.provider_payment_id = f"demo_{payment.id}"
        await BillingService().complete_payment(session, payment)
        return {"ok": True, "demo": True}
    inv_id = await next_invoice_id()
    url = build_payment_url(
        payment_id=str(payment.id),
        inv_id=inv_id,
        amount_rub=pkg.price_rub,
        description=f"Лея · {pkg.title}"[:100],
        success_url=f"{settings.public_base_url.rstrip('/')}/lk",
        fail_url=f"{settings.public_base_url.rstrip('/')}/lk?pay=fail",
    )
    payment.provider_payment_id = str(inv_id)
    payload = dict(payment.payload or {})
    payload["payment_url"] = url
    payload["inv_id"] = str(inv_id)
    payment.payload = payload
    return {"ok": True, "payment_url": url}


async def cabinet_payload(session: AsyncSession, user: User) -> dict:
    from app.services.products.entitlements import EntitlementService
    from app.services.products.packages import PACKAGES

    ident = await session.scalar(select(WebIdentity).where(WebIdentity.user_id == user.id))
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
        readings = [public_reading(row, include_paid=row.status in {"paid", "ready"}) for row in rows]
    ent = EntitlementService()
    plan = await ent.active_plan_label(user.id)
    vip = await ent.has_vip(user.id)
    love_plus = await ent.has_love_plus(user.id)
    return {
        "user": {
            "id": user.id,
            "name": (ident.name if ident else None) or user.first_name,
            "email": ident.email if ident else None,
        },
        "plan": plan,
        "vip": vip,
        "love_plus": love_plus,
        "readings": readings,
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
    from app.database.models import Message, MessageRole
    from app.services.products.entitlements import EntitlementService

    text = (text or "").strip()
    if len(text) < 2:
        raise ValueError("Напиши сообщение")
    if len(text) > 4000:
        raise ValueError("Слишком длинно")
    reading = None
    if reading_token:
        reading = await session.scalar(select(WebReading).where(WebReading.token == reading_token))
        if reading is None:
            raise ValueError("Разбор не найден")
    vip = await EntitlementService().has_vip(user.id)
    paid = bool(reading and reading.status in {"paid", "ready"} and reading.paid_text)
    if not vip and not paid:
        raise ValueError("Чат по разбору — после оплаты. Свободный чат — с VIP.")
    history = list(
        (
            await session.scalars(
                select(Message)
                .where(Message.user_id == user.id)
                .order_by(Message.created_at.desc())
                .limit(12)
            )
        ).all()
    )
    history.reverse()
    system = (
        "Ты Лея, ИИ-таролог, не живой человек. Пиши на «ты», коротко и по делу. "
        "Не давай медсоветов, юридических гарантий и предсказаний смерти."
    )
    if reading:
        system += (
            f"\nКонтекст разбора «{reading.card_id}». Мини: {json.dumps(reading.mini, ensure_ascii=False)[:2500]}"
        )
        if paid:
            system += f"\nПолный текст:\n{(reading.paid_text or '')[:5000]}"
    messages = [{"role": "system", "content": system}]
    for row in history:
        if (row.meta or {}).get("reading_token") not in {None, reading_token}:
            continue
        messages.append({"role": "user" if row.role == MessageRole.USER.value else "assistant", "content": row.content})
    messages.append({"role": "user", "content": text})
    reply = await KieClient().chat_completion(messages, reasoning_effort="low")
    meta = {"channel": "web", "reading_token": reading_token}
    session.add(Message(user_id=user.id, role=MessageRole.USER.value, content=text, meta=meta))
    session.add(Message(user_id=user.id, role=MessageRole.ASSISTANT.value, content=reply, meta=meta))
    await session.flush()
    return {"reply": reply}

