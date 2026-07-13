import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy import func, select

from app.bot.formatting import to_telegram_html
from app.bot.leia_keyboards import inline_broadcast_products
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
from app.services.products.service import ProductService
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


def _morning_trial_active(settings: UserSettings, today: date) -> bool:
    ends = settings.free_morning_week_ends_at
    if ends is None:
        return True
    return today <= ends


class LeiaBroadcastService:
    async def tick(self, bot: Bot) -> None:
        for fn in (
            self._send_morning,
            self._send_weekly,
            self._send_evening,
            self._send_funnel_day2,
            self._send_pending_mini_portraits,
        ):
            try:
                await fn(bot)
            except Exception:
                logger.exception("leia broadcast %s failed", fn.__name__)

    async def _onboarded_users(self, session):
        rows = await session.execute(
            select(User, UserSettings, SoulProfile)
            .join(UserSettings, UserSettings.user_id == User.id)
            .outerjoin(SoulProfile, SoulProfile.user_id == User.id)
            .where(User.is_onboarded.is_(True), User.is_blocked.is_(False))
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
            candidates = await self._onboarded_users(session)

        sent = 0
        tarot = TarotService()
        keyboard = inline_broadcast_products()

        for user, user_settings, profile in candidates:
            if sent >= BATCH:
                break
            if not user_settings.morning_digest_enabled:
                continue

            now_local = _local_now(user_settings.timezone)
            today = now_local.date()
            if now_local.hour < MORNING_HOUR:
                continue
            if _is_quiet(now_local, user_settings.quiet_hours_start, user_settings.quiet_hours_end):
                continue
            if not _morning_trial_active(user_settings, today):
                continue

            async with AsyncSessionLocal() as session:
                already = await session.scalar(
                    select(DailyPrediction.id).where(
                        DailyPrediction.user_id == user.id,
                        DailyPrediction.prediction_date == today,
                    )
                )
            if already:
                continue

            name = (profile.name if profile and profile.name else None) or user.first_name or "дорогая"
            birth = profile.birth_date if profile else None

            try:
                _interpretation, card = await tarot.daily_card_for_telegram(user.telegram_id)
                card_name = str(card.get("name", "Карта дня")) if card else "Карта дня"
                card_meaning = str(card.get("description", "")) if card else "послание на сегодня"
                text = format_morning_message(
                    name=name,
                    for_day=today,
                    birth=birth,
                    card_name=card_name,
                    card_meaning=card_meaning,
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
                    async with AsyncSessionLocal() as session:
                        await self._record_sent(session, user.id, "leia_morning", text)
                    sent += 1
            except Exception as exc:
                logger.warning("Morning broadcast failed for %s: %s", user.telegram_id, exc)

    async def _send_weekly(self, bot: Bot) -> None:
        async with AsyncSessionLocal() as session:
            candidates = await self._onboarded_users(session)

        sent = 0
        keyboard = inline_broadcast_products()

        for user, user_settings, profile in candidates:
            if sent >= BATCH:
                break
            if not user_settings.weekly_horoscope_enabled:
                continue

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
            candidates = await self._onboarded_users(session)

        sent = 0
        keyboard = inline_broadcast_products()

        for user, user_settings, profile in candidates:
            if sent >= BATCH:
                break
            if not user_settings.proactive_messages_enabled:
                continue

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
        keyboard = inline_broadcast_products()

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

    async def _send_pending_mini_portraits(self, bot: Bot) -> None:
        """Мини-портрет тем, кто не выбрал продукт и ещё не получал портрет."""
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(User, UserSettings, SoulProfile)
                .join(UserSettings, UserSettings.user_id == User.id)
                .outerjoin(SoulProfile, SoulProfile.user_id == User.id)
                .where(
                    User.is_onboarded.is_(True),
                    User.is_blocked.is_(False),
                    UserSettings.mini_portrait_sent_at.is_(None),
                )
                .limit(50)
            )
            candidates = rows.all()

        sent = 0
        service = ProductService()
        keyboard = inline_broadcast_products()

        for user, user_settings, profile in candidates:
            if sent >= BATCH:
                break
            if user.created_at and user.created_at > datetime.now(UTC) - timedelta(hours=2):
                continue
            if profile is None or profile.birth_date is None:
                continue

            async with AsyncSessionLocal() as session:
                usage_count = await session.scalar(
                    select(func.count()).select_from(ProductUsage).where(
                        ProductUsage.user_id == user.id
                    )
                ) or 0
            if usage_count > 0:
                continue

            try:
                text = await service.generate_mini_portrait(user.id)
                ok = await send_bot_html(
                    bot, user.telegram_id, to_telegram_html(text), reply_markup=keyboard
                )
                if ok:
                    async with AsyncSessionLocal() as session:
                        settings = await session.scalar(
                            select(UserSettings).where(UserSettings.user_id == user.id)
                        )
                        if settings:
                            settings.mini_portrait_sent_at = datetime.now(UTC)
                            await session.commit()
                    sent += 1
            except Exception as exc:
                logger.warning("Mini portrait broadcast failed for %s: %s", user.telegram_id, exc)
