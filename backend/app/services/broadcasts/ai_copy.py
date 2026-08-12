"""AI-слои бесплатных рассылок Леи (знак → персональное)."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.bot.leia_rich import normalize_leia_rich
from app.database.models import Notification
from app.database.session import AsyncSessionLocal
from app.services.ai.kie_client import KieClient
from app.services.astrology.service import AstrologyService
from app.services.astrology.zodiac import SIGNS, zodiac_sign
from app.services.broadcasts.content import (
    format_morning_message,
    format_weekly_horoscope,
)
from app.services.numerology.service import NumerologyService
from app.services.products.prompts import assemble_system

logger = logging.getLogger(__name__)

_SIGN_NAMES = list(dict.fromkeys(name for name, *_ in SIGNS))

# In-process cache: (kind, date_iso, sign) → text
_cache: dict[tuple[str, str, str], str] = {}


def _sign_emoji(sign: str) -> str:
    for name, emoji, *_ in SIGNS:
        if name == sign:
            return emoji
    return "♈"


async def last_7_summaries(user_id: str, *, limit: int = 14) -> str:
    """Выжимки утренних/недельных рассылок за 7 дней."""
    since = datetime.now(UTC) - timedelta(days=7)
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.kind.in_(("leia_morning", "leia_weekly")),
                    Notification.scheduled_at >= since,
                )
                .order_by(Notification.scheduled_at.desc())
                .limit(limit)
            )
        ).all()
    snippets: list[str] = []
    for row in rows:
        payload = row.payload or {}
        text = str(payload.get("text") or "")
        if not text:
            continue
        # короткая выжимка без заголовков
        compact = " ".join(text.replace("#", "").split())
        snippets.append(compact[:220])
    return "\n".join(f"- {s}" for s in snippets) if snippets else "нет"


async def _complete(system: str, user: str, *, feature: str) -> str:
    kie = KieClient()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        text = normalize_leia_rich(await kie.chat_completion(messages)).strip()
        return text
    except Exception as exc:
        logger.warning("Broadcast AI %s failed: %s", feature, exc)
        return ""


async def sign_forecast_for_day(sign: str, for_day: date) -> str:
    key = ("daily_sign", for_day.isoformat(), sign)
    if key in _cache:
        return _cache[key]
    vars_ = {
        "sign": sign,
        "date": for_day.strftime("%d.%m.%Y"),
    }
    system = assemble_system("daily_sign", vars_)
    text = await _complete(
        system,
        f"Напиши прогноз на {vars_['date']} для знака {sign}.",
        feature="daily_sign",
    )
    if text:
        _cache[key] = text
    return text


async def weekly_forecast_for_sign(sign: str, for_day: date, *, last_7: str = "нет") -> str:
    key = ("weekly", for_day.isoformat(), sign)
    if key in _cache:
        return _cache[key]
    dates = AstrologyService().week_range_label(for_day)
    # week_arcana без ДР — по номеру недели как общий для знака
    week_num = for_day.isocalendar().week
    from app.services.numerology.matrix import arcana_label, arcana_reduce

    week_arcana = arcana_label(arcana_reduce(week_num))
    vars_ = {
        "sign": sign,
        "dates": dates,
        "week_arcana": week_arcana,
        "last_7": last_7 or "нет",
        "date": for_day.strftime("%d.%m.%Y"),
    }
    system = assemble_system("weekly", vars_)
    text = await _complete(
        system,
        f"Напиши недельный прогноз для знака {sign} на {dates}.",
        feature="weekly_sign",
    )
    if text:
        _cache[key] = text
    return text


async def build_morning_text(
    *,
    user_id: str,
    name: str,
    birth: date | None,
    for_day: date,
) -> str:
    if birth is None:
        return format_morning_message(
            name=name,
            for_day=for_day,
            birth=None,
            sign_forecast="Укажи дату рождения в анкете — прогноз станет точным.",
            personal_block="Пока без личного числа — заполни анкету.",
            action="Открой профиль и допиши дату рождения.",
        )

    sign, emoji = zodiac_sign(birth)
    sign_text = await sign_forecast_for_day(sign, for_day)
    if not sign_text:
        # fallback: короткий шаблонный
        from app.services.broadcasts.content import SIGN_DAILY

        tip = SIGN_DAILY.get(sign, "смотри на одну важную мелочь сегодня")
        sign_text = f"Сегодня у {sign} день про мелочи, которые решают. {tip.capitalize()}."

    last_7 = await last_7_summaries(user_id)
    vars_ = NumerologyService().prompt_vars(
        name=name,
        birth=birth,
        for_day=for_day,
        last_7=last_7,
        sign_forecast=sign_text,
    )
    system = assemble_system("daily_personal", vars_)
    personal = await _complete(
        system,
        "Напиши только персональное уточнение и одно дело на сегодня.",
        feature="daily_personal",
    )
    if not personal:
        personal = (
            f"Личное число дня — **{vars_['personal_day']}**. "
            "Сузь общий прогноз до одной сферы и не распыляйся."
        )
        action = "Сделай одно конкретное дело до обеда — и остановись."
    else:
        # выдели «одно дело» если модель смешала
        action = ""
        lines = [ln.strip() for ln in personal.split("\n") if ln.strip()]
        if len(lines) >= 2 and len(lines[-1]) < 160:
            action = lines[-1]
            personal = "\n".join(lines[:-1])
        if not action:
            action = "Одно дело: закрой то, что висит с вчера — одним сообщением или звонком."

    return format_morning_message(
        name=name,
        for_day=for_day,
        birth=birth,
        sign_forecast=sign_text,
        personal_block=personal,
        action=action,
        sign=sign,
        sign_emoji=emoji,
        personal_day=int(vars_["personal_day"]) if str(vars_["personal_day"]).isdigit() else 0,
    )


async def build_weekly_text(
    *,
    user_id: str,
    name: str,
    birth: date | None,
    for_day: date,
) -> str:
    if birth is None:
        return format_weekly_horoscope(name=name, birth=None, for_day=for_day, body="")

    sign, emoji = zodiac_sign(birth)
    last_7 = await last_7_summaries(user_id)
    body = await weekly_forecast_for_sign(sign, for_day, last_7=last_7)
    if not body:
        return format_weekly_horoscope(name=name, birth=birth, for_day=for_day, body="")
    return format_weekly_horoscope(
        name=name,
        birth=birth,
        for_day=for_day,
        body=body,
        sign=sign,
        sign_emoji=emoji,
    )


async def warm_daily_sign_cache(for_day: date) -> None:
    """Опционально: прогреть 12 знаков одним проходом."""
    for sign in _SIGN_NAMES:
        await sign_forecast_for_day(sign, for_day)
