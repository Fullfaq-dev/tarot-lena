"""AI-слои бесплатных рассылок Леи (знак → персональное)."""

from __future__ import annotations

import logging
from collections import defaultdict
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
from app.services.broadcasts.daily_themes import (
    NUMBER_MEANINGS_BLOCK,
    compute_link_type,
    format_last7_bans,
    sign_theme_for,
)
from app.services.numerology.service import NumerologyService
from app.services.products.prompts import assemble_system

logger = logging.getLogger(__name__)

_SIGN_NAMES = list(dict.fromkeys(name for name, *_ in SIGNS))

# In-process cache: (kind, date_iso, sign) → text
_cache: dict[tuple[str, str, str], str] = {}
# Антиповтор слоя 1 по знаку (выжимки прошлых дней)
_sign_history: dict[str, list[str]] = defaultdict(list)


def _sign_emoji(sign: str) -> str:
    for name, emoji, *_ in SIGNS:
        if name == sign:
            return emoji
    return "♈"


def _summary_line(for_day: date, *, image: str, advice: str) -> str:
    img = " ".join(image.replace("#", "").split())[:90]
    adv = " ".join(advice.replace("#", "").split())[:90]
    return f"{for_day.strftime('%d.%m')} — образ: {img}; совет: {adv}"


async def last_7_summaries(user_id: str, *, limit: int = 14) -> str:
    """Список запретов за 7 дней (формат из ТЗ)."""
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
    entries: list[str] = []
    for row in rows:
        payload = row.payload or {}
        summary = str(payload.get("summary") or "").strip()
        if summary:
            entries.append(summary)
            continue
        text = str(payload.get("text") or "")
        if not text:
            continue
        compact = " ".join(text.replace("#", "").split())[:160]
        when = row.scheduled_at.strftime("%d.%m") if row.scheduled_at else "—"
        entries.append(f"{when} — образ: {compact}; совет: —")
    return format_last7_bans(entries)


async def recent_had_sport(user_id: str, *, days: int = 5) -> bool:
    since = datetime.now(UTC) - timedelta(days=days)
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.kind == "leia_morning",
                    Notification.scheduled_at >= since,
                )
                .order_by(Notification.scheduled_at.desc())
                .limit(10)
            )
        ).all()
    for row in rows:
        if str((row.payload or {}).get("link_type") or "") == "СПОР":
            return True
    return False


def _strip_md_headings(text: str) -> str:
    lines = []
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


async def _complete(system: str, user: str, *, feature: str) -> str:
    kie = KieClient()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        text = normalize_leia_rich(await kie.chat_completion(messages)).strip()
        if feature.startswith("daily_"):
            text = _strip_md_headings(text)
        return text
    except Exception as exc:
        logger.warning("Broadcast AI %s failed: %s", feature, exc)
        return ""


async def sign_forecast_for_day(sign: str, for_day: date) -> str:
    theme = sign_theme_for(sign, for_day)
    key = ("daily_sign", for_day.isoformat(), f"{sign}:{theme}")
    if key in _cache:
        return _cache[key]

    hist = _sign_history.get(sign, [])[-7:]
    last_7 = format_last7_bans(
        [
            f"{for_day.strftime('%d.%m')} — образ: {h}; совет: —"
            for h in hist
        ]
    )
    vars_ = {
        "sign": sign,
        "date": for_day.strftime("%d.%m.%Y"),
        "sign_theme": theme,
        "last_7": last_7,
        "number_meanings": NUMBER_MEANINGS_BLOCK,
    }
    system = assemble_system("daily_sign", vars_)
    text = await _complete(
        system,
        f"Напиши прогноз на {vars_['date']} для знака {sign}. Домен строго: {theme}.",
        feature="daily_sign",
    )
    if text:
        _cache[key] = text
        _sign_history[sign].append(" ".join(text.split())[:100])
        _sign_history[sign] = _sign_history[sign][-14:]
    return text


async def weekly_forecast_for_sign(sign: str, for_day: date, *, last_7: str = "нет") -> str:
    key = ("weekly", for_day.isoformat(), sign)
    if key in _cache:
        return _cache[key]
    dates = AstrologyService().week_range_label(for_day)
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
) -> tuple[str, dict]:
    """Возвращает (текст сообщения, meta для Notification.payload)."""
    meta: dict = {}
    if birth is None:
        text = format_morning_message(
            name=name,
            for_day=for_day,
            birth=None,
            sign_forecast="Укажи дату рождения в анкете — прогноз станет точным.",
            personal_block="Пока без личного числа — заполни анкету.",
            action="Открой профиль и допиши дату рождения.",
        )
        return text, meta

    sign, emoji = zodiac_sign(birth)
    theme = sign_theme_for(sign, for_day)
    sign_text = await sign_forecast_for_day(sign, for_day)
    if not sign_text:
        from app.services.broadcasts.content import SIGN_DAILY

        tip = SIGN_DAILY.get(sign, "смотри на одну важную мелочь сегодня")
        sign_text = f"Сегодня у {sign} день про {theme}. {tip.capitalize()}."

    last_7 = await last_7_summaries(user_id)
    vars_ = NumerologyService().prompt_vars(
        name=name,
        birth=birth,
        for_day=for_day,
        last_7=last_7,
        sign_forecast=sign_text,
    )
    personal_day = int(vars_["personal_day"]) if str(vars_["personal_day"]).isdigit() else 1
    force_sport = not await recent_had_sport(user_id, days=5)
    link_type = compute_link_type(personal_day, theme, force_sport=force_sport)
    vars_["link_type"] = link_type
    vars_["sign_theme"] = theme
    vars_["number_meanings"] = NUMBER_MEANINGS_BLOCK

    system = assemble_system("daily_personal", vars_)
    personal = await _complete(
        system,
        (
            f"Связка строго: {link_type}. Число дня: {personal_day}. "
            "Напиши уточнение и отдельной последней строкой — дело с глагола."
        ),
        feature="daily_personal",
    )
    if not personal:
        personal = (
            f"Личное число дня — **{personal_day}** ({link_type}). "
            f"Сегодня держись темы числа, а не общего фона знака."
        )
        action = "Сделай одно конкретное дело по теме своего числа — до обеда."
    else:
        action = ""
        lines = [ln.strip() for ln in personal.split("\n") if ln.strip()]
        if len(lines) >= 2 and len(lines[-1]) < 180:
            action = lines[-1]
            personal = "\n".join(lines[:-1])
        if not action:
            action = "Сделай одно конкретное дело по теме своего числа — до обеда."

    text = format_morning_message(
        name=name,
        for_day=for_day,
        birth=birth,
        sign_forecast=sign_text,
        personal_block=personal,
        action=action,
        sign=sign,
        sign_emoji=emoji,
        personal_day=personal_day,
    )
    meta = {
        "link_type": link_type,
        "sign_theme": theme,
        "personal_day": personal_day,
        "summary": _summary_line(for_day, image=sign_text, advice=action),
    }
    return text, meta


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
    for sign in _SIGN_NAMES:
        await sign_forecast_for_day(sign, for_day)
