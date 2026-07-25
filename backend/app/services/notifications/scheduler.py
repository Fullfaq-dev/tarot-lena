import logging
from datetime import UTC, datetime

from aiogram import Bot
from sqlalchemy import select

from app.core.config import get_settings
from app.database.models import Notification, NotificationLog, User
from app.database.session import AsyncSessionLocal
from app.services.broadcasts import LeiaBroadcastService
from app.services.notifications.delivery import deliver_notification

logger = logging.getLogger(__name__)


class NotificationScheduler:
    async def tick(self) -> None:
        settings = get_settings()
        if not settings.telegram_bot_token or settings.telegram_bot_token == "replace-me":
            return
        async with Bot(token=settings.telegram_bot_token) as bot:
            try:
                await LeiaBroadcastService().tick(bot)
            except Exception:
                logger.exception("leia broadcast scheduler failed")
            try:
                await self._deliver_due_notifications(bot)
            except Exception:
                logger.exception("notification delivery failed")

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
                ok = False
                if not user.is_blocked:
                    ok = await deliver_notification(bot, user, notification)
                notification.sent_at = datetime.now(UTC)
                session.add(
                    NotificationLog(
                        notification_id=notification.id,
                        user_id=notification.user_id,
                        status="sent" if ok else "skipped",
                        message="Delivered via Telegram." if ok else "Empty or failed delivery.",
                    )
                )
            await session.commit()
