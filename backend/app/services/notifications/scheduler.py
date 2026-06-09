from datetime import UTC, datetime

from sqlalchemy import select

from app.database.models import Notification, NotificationLog
from app.database.session import AsyncSessionLocal


class NotificationScheduler:
    async def tick(self) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Notification)
                .where(Notification.sent_at.is_(None))
                .where(Notification.scheduled_at <= datetime.now(UTC))
                .limit(25)
            )
            for notification in result.scalars():
                notification.sent_at = datetime.now(UTC)
                session.add(
                    NotificationLog(
                        notification_id=notification.id,
                        user_id=notification.user_id,
                        status="queued",
                        message="Notification is ready for Telegram delivery.",
                    )
                )
            await session.commit()
