import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy import func, select

from app.bot.formatting import to_telegram_html
from app.bot.leia_keyboards import inline_product_menu
from app.database.models import (
    DailyPrediction,
    Message,
    Notification,
    ProductUsage,
    SoulProfile,
    User,
    UserSettings,
)
from app.database.session import AsyncSessionLocal
from app.services.broadcasts.content import (
    format_evening_nudge,
    format_funnel_day2,
    format_morning_message,
    format_weekly_horoscope,
)
from app.services.tarot.service import TarotService
from app.services.telegram_notify import send_bot_html, send_bot_photo

logger = logging.getLogger(__name__)

MORNING_HOUR = 9
EVENING_HOUR = 20
WEEKLY_WEEKDAY = 0  # Monday
BATCH = 20
FUNNEL_DAY_MIN = 2
FUNNEL_DAY_MAX = 3


def _parse_hm(value: str, default: int) -> int:
    try:
        return int(value.split(":", 1)[0])
    except Exception:
        return default


def _is_quiet(now_local: datetime, quiet_start: str, quiet_end: str) -> bool:
    start = _parse_hm(quiet_start, 22)
    end = _parse_hm(quiet_end, 9)
    hour = now_local.hour
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def _local_now(timezone_name: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(timezone_name))
    except Exception:
        return datetime.now(UTC)


def _local_day_bounds(now_local: datetime) -> tuple[datetime, datetime]:
    start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


class LeiaBroadcastService:
    async def tick(self, bot: Bot) -> None:
        try:
            await self._send_morning(bot)
        except Exception:
            logger.exception("leia morning broadcast failed")
        try:
            await self._send_weekly(bot)
        except Exception:
            logger.exception("leia weekly broadcast failed")
        try:
            await self._send_evening(bot)
        except Exception:
            logger.exception("leia evening broadcast failed")
        try:
            await self._send_funnel_day2(bot)
        except Exception:
            logger.exception("leia funnel day2 failed")

    async def _eligible(self, session, *, morning: bool, evening: bool):
        if morning:
            column = UserSettings.daily_card_enabled
        elif evening:
            column = UserSettings.proactive_messages_enabled
        else:
            column = UserSettings.daily_card_enabled
        rows = await session.execute(
            select(User, UserSettings, SoulProfile)
            .join(UserSettings, UserSettings.user_id == User.id)
            .outerjoin(SoulProfile, SoulProfile.user_id == User.id)
            .where(
                User.is_onboarded.is_(True),
                User.is_blocked.is_(False),
                column.is_(True),
            )
            .limit(500)
        )
        return rows.all()

    async def _already_sent_kind(
        self, session, user_id: str, kind: str, since_local: datetime
    ) -> bool:
        since_utc = since_local.astimezone(UTC)
        row = await session.scalar(
            select(Notification.id).where(
                Notification.user_id == user_id,
                Notification.kind == kind,
                Notification.scheduled_at >= since_utc,
            )
        )
        return row is not None

    async def _record_sent(self, session, user_id: str, kind: str, text: str) -> None:
        now = datetime.now(UTC)
        session.add(
            Notification(
                user_id=user_id,
                kind=kind,
                scheduled_at=now,
                sent_at=now,
                payload={"text": text},
            )
        )
        await session.commit()

    async def _send_morning(self, bot: Bot) -> None:
        async with AsyncSessionLocal() as session:
            candidates = await self._eligible(session, morning=True, evening=False)

        sent = 0
        tarot = TarotService()
        keyboard = inline_product_menu()

        for user, user_settings, profile in candidates:
            if sent >= BATCH:
                break
            now_local = _local_now(user_settings.timezone)
            if now_local.hour < MORNING_HOUR:
                continue
            if _is_quiet(now_local, user_settings.quiet_hours_start, user_settings.quiet_hours_end):
                continue

            async with AsyncSessionLocal() as session:
                already = await session.scalar(
                    select(DailyPrediction.id).where(
                        DailyPrediction.user_id == user.id,
                        DailyPrediction.prediction_date == now_local.date(),
                    )
                )
            if already:
                continue

            name = (profile.name if profile and profile.name else None) or user.first_name or "дорогая"
            birth = profile.birth_date if profile else None

            try:
                interpretation, card = await tarot.daily_card_for_telegram(user.telegram_id)
                text = format_morning_message(
                    name=name,
                    for_day=now_local.date(),
                    birth=birth,
                    card_text=interpretation.strip(),
                )
                if card is None:
                    ok = await send_bot_html(
                        bot, user.telegram_id, to_telegram_html(text), reply_markup=keyboard
                    )
                else:
                    ok = await send_bot_photo(
                        bot,
                        user.telegram_id,
                        str(card.get("image_path", "")),
                        caption_html=to_telegram_html(text),
                        caption_plain=text,
                        reply_markup=keyboard,
                    )
                if ok:
                    await tarot.record_daily_card_context(
                        user.telegram_id,
                        interpretation.strip(),
                        card_name=str(card.get("name", "")) if card else "",
                    )
                    async with AsyncSessionLocal() as session:
                        await self._record_sent(session, user.id, "leia_morning", text)
                    sent += 1
            except Exception as exc:
                logger.warning("Morning broadcast failed for %s: %s", user.telegram_id, exc)

    async def _send_weekly(self, bot: Bot) -> None:
        async with AsyncSessionLocal() as session:
            candidates = await self._eligible(session, morning=True, evening=False)

        sent = 0
        keyboard = inline_product_menu()

        for user, user_settings, profile in candidates:
            if sent >= BATCH:
                break
            now_local = _local_now(user_settings.timezone)
            if now_local.weekday() != WEEKLY_WEEKDAY or now_local.hour < MORNING_HOUR:
                continue
            if _is_quiet(now_local, user_settings.quiet_hours_start, user_settings.quiet_hours_end):
                continue

            week_start = (now_local - timedelta(days=now_local.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            async with AsyncSessionLocal() as session:
                if await self._already_sent_kind(session, user.id, "leia_weekly", week_start):
                    continue

            name = (profile.name if profile and profile.name else None) or user.first_name or "дорогая"
            birth = profile.birth_date if profile else None
            text = format_weekly_horoscope(name=name, birth=birth, for_day=now_local.date())

            ok = await send_bot_html(
                bot, user.telegram_id, to_telegram_html(text), reply_markup=keyboard
            )
            if ok:
                async with AsyncSessionLocal() as session:
                    await self._record_sent(session, user.id, "leia_weekly", text)
                sent += 1

    async def _send_evening(self, bot: Bot) -> None:
        async with AsyncSessionLocal() as session:
            candidates = await self._eligible(session, morning=False, evening=True)

        sent = 0
        keyboard = inline_product_menu()

        for user, user_settings, profile in candidates:
            if sent >= BATCH:
                break
            now_local = _local_now(user_settings.timezone)
            if now_local.hour < EVENING_HOUR:
                continue
            if _is_quiet(now_local, user_settings.quiet_hours_start, user_settings.quiet_hours_end):
                continue

            day_start, day_end = _local_day_bounds(now_local)
            day_start_utc = day_start.astimezone(UTC)
            day_end_utc = day_end.astimezone(UTC)

            async with AsyncSessionLocal() as session:
                if await self._already_sent_kind(session, user.id, "leia_evening", day_start):
                    continue
                active_today = await session.scalar(
                    select(Message.id).where(
                        Message.user_id == user.id,
                        Message.created_at >= day_start_utc,
                        Message.created_at < day_end_utc,
                    )
                )
            if active_today:
                continue

            name = (profile.name if profile and profile.name else None) or user.first_name or "дорогая"
            text = format_evening_nudge(name=name)
            ok = await send_bot_html(
                bot, user.telegram_id, to_telegram_html(text), reply_markup=keyboard
            )
            if ok:
                async with AsyncSessionLocal() as session:
                    await self._record_sent(session, user.id, "leia_evening", text)
                sent += 1

    async def _send_funnel_day2(self, bot: Bot) -> None:
        now = datetime.now(UTC)
        window_start = now - timedelta(days=FUNNEL_DAY_MAX)
        window_end = now - timedelta(days=FUNNEL_DAY_MIN)

        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(User, SoulProfile)
                .outerjoin(SoulProfile, SoulProfile.user_id == User.id)
                .where(
                    User.is_onboarded.is_(True),
                    User.is_blocked.is_(False),
                    User.created_at >= window_start,
                    User.created_at <= window_end,
                )
                .limit(100)
            )
            candidates = rows.all()

        sent = 0
        keyboard = inline_product_menu()

        for user, profile in candidates:
            if sent >= BATCH:
                break

            async with AsyncSessionLocal() as session:
                usage_count = await session.scalar(
                    select(func.count()).select_from(ProductUsage).where(
                        ProductUsage.user_id == user.id
                    )
                ) or 0
                if usage_count > 0:
                    continue
                ever_sent = await session.scalar(
                    select(Notification.id).where(
                        Notification.user_id == user.id,
                        Notification.kind == "leia_funnel_day2",
                    )
                )
                if ever_sent:
                    continue

            name = (profile.name if profile and profile.name else None) or user.first_name or "дорогая"
            text = format_funnel_day2(name=name)
            ok = await send_bot_html(
                bot, user.telegram_id, to_telegram_html(text), reply_markup=keyboard
            )
            if ok:
                async with AsyncSessionLocal() as session:
                    await self._record_sent(session, user.id, "leia_funnel_day2", text)
                sent += 1
