from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Notification, RelationshipPerson, User


class NotificationService:
    async def schedule_daily_card(self, session: AsyncSession, user: User, hour: int = 9) -> Notification:
        now = datetime.now(UTC)
        scheduled = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if scheduled <= now:
            scheduled += timedelta(days=1)
        notification = Notification(
            user_id=user.id,
            kind="daily_card",
            scheduled_at=scheduled,
            payload={"text": "Твой прогноз на сегодня уже готов."},
        )
        session.add(notification)
        return notification

    async def schedule_relationship_followup(
        self,
        session: AsyncSession,
        user: User,
        person: RelationshipPerson,
        days: int = 30,
    ) -> Notification:
        notification = Notification(
            user_id=user.id,
            kind="relationship_followup",
            scheduled_at=datetime.now(UTC) + timedelta(days=days),
            payload={
                "person_id": person.id,
                "text": f"В прошлый раз ты рассказывал(а) о {person.display_name}. Изменилось ли что-то?",
            },
        )
        session.add(notification)
        return notification

    async def schedule_reactivation(self, session: AsyncSession, user: User, days: int = 7) -> Notification:
        notification = Notification(
            user_id=user.id,
            kind="reactivation",
            scheduled_at=datetime.now(UTC) + timedelta(days=days),
            payload={"text": "Ты давно не заходил(а). Хочешь узнать, какой цикл сейчас открывается?"},
        )
        session.add(notification)
        return notification
