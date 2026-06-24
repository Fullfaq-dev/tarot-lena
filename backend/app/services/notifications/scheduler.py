import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy import func, select

from app.bot.formatting import to_telegram_html
from app.bot.i18n import normalize_language, t
from app.core.config import get_settings
from app.database.models import (
    DailyPrediction,
    Message,
    Notification,
    NotificationLog,
    User,
    UserSettings,
)
from app.database.session import AsyncSessionLocal
from app.services.telegram_notify import send_bot_html, send_bot_photo
from app.services.tarot.service import TarotService

logger = logging.getLogger(__name__)

DAILY_CARD_HOUR = 9
PROACTIVE_INACTIVE_DAYS = 7
PROACTIVE_COOLDOWN_DAYS = 7
DAILY_BATCH = 20
PROACTIVE_BATCH = 10


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


class NotificationScheduler:
    async def tick(self) -> None:
        settings = get_settings()
        if not settings.telegram_bot_token or settings.telegram_bot_token == "replace-me":
            return
        async with Bot(token=settings.telegram_bot_token) as bot:
            try:
                await self._send_daily_cards(bot)
            except Exception:
                logger.exception("daily card scheduler failed")
            try:
                await self._send_proactive(bot)
            except Exception:
                logger.exception("proactive scheduler failed")
            try:
                await self._deliver_due_notifications(bot)
            except Exception:
                logger.exception("notification delivery failed")

    async def _eligible_settings(self, session, *, daily: bool):
        column = (
            UserSettings.daily_card_enabled if daily else UserSettings.proactive_messages_enabled
        )
        rows = await session.execute(
            select(User, UserSettings)
            .join(UserSettings, UserSettings.user_id == User.id)
            .where(
                User.is_onboarded.is_(True),
                User.is_blocked.is_(False),
                column.is_(True),
            )
            .limit(500)
        )
        return rows.all()

    async def _send_daily_cards(self, bot: Bot) -> None:
        async with AsyncSessionLocal() as session:
            candidates = await self._eligible_settings(session, daily=True)

        sent = 0
        for user, user_settings in candidates:
            if sent >= DAILY_BATCH:
                break
            now_local = _local_now(user_settings.timezone)
            if now_local.hour < DAILY_CARD_HOUR:
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

            try:
                tarot = TarotService()
                interpretation, card = await tarot.daily_card_for_telegram(user.telegram_id)
                if card is None:
                    ok = await send_bot_html(bot, user.telegram_id, to_telegram_html(interpretation))
                else:
                    plain = interpretation.strip()
                    ok = await send_bot_photo(
                        bot,
                        user.telegram_id,
                        str(card.get("image_path", "")),
                        caption_html=to_telegram_html(plain),
                        caption_plain=plain,
                    )
                if ok:
                    await tarot.record_daily_card_context(
                        user.telegram_id,
                        interpretation.strip(),
                        card_name=str(card.get("name", "")) if card else "",
                    )
                    sent += 1
            except Exception as exc:
                logger.warning("Daily card send failed for %s: %s", user.telegram_id, exc)

    async def _send_proactive(self, bot: Bot) -> None:
        async with AsyncSessionLocal() as session:
            candidates = await self._eligible_settings(session, daily=False)

        now = datetime.now(UTC)
        inactive_before = now - timedelta(days=PROACTIVE_INACTIVE_DAYS)
        cooldown_before = now - timedelta(days=PROACTIVE_COOLDOWN_DAYS)

        sent = 0
        for user, user_settings in candidates:
            if sent >= PROACTIVE_BATCH:
                break
            now_local = _local_now(user_settings.timezone)
            if now_local.hour < 11 or now_local.hour >= 20:
                continue
            if _is_quiet(now_local, user_settings.quiet_hours_start, user_settings.quiet_hours_end):
                continue

            async with AsyncSessionLocal() as session:
                last_message_at = await session.scalar(
                    select(func.max(Message.created_at)).where(Message.user_id == user.id)
                )
                if last_message_at is not None and last_message_at > inactive_before:
                    continue
                last_proactive_at = await session.scalar(
                    select(func.max(Notification.scheduled_at)).where(
                        Notification.user_id == user.id,
                        Notification.kind == "reactivation",
                    )
                )
                if last_proactive_at is not None and last_proactive_at > cooldown_before:
                    continue

                lang = normalize_language(user_settings.ui_language)
                notification = Notification(
                    user_id=user.id,
                    kind="reactivation",
                    scheduled_at=now,
                    sent_at=now,
                    payload={"text": t("proactive_nudge", lang)},
                )
                session.add(notification)
                await session.commit()

            ok = await send_bot_html(bot, user.telegram_id, t("proactive_nudge", lang))
            if ok:
                sent += 1

    async def _deliver_due_notifications(self, bot: Bot) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Notification, User)
                .join(User, User.id == Notification.user_id)
                .where(Notification.sent_at.is_(None))
                .where(Notification.scheduled_at <= datetime.now(UTC))
                .limit(25)
            )
            rows = result.all()
            for notification, user in rows:
                text = ""
                if isinstance(notification.payload, dict):
                    text = str(notification.payload.get("text", ""))
                if text and not user.is_blocked:
                    await send_bot_html(bot, user.telegram_id, text)
                notification.sent_at = datetime.now(UTC)
                session.add(
                    NotificationLog(
                        notification_id=notification.id,
                        user_id=notification.user_id,
                        status="sent",
                        message="Delivered via Telegram.",
                    )
                )
            await session.commit()
