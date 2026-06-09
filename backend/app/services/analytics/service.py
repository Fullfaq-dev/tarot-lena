from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AnalyticsEvent, User


class AnalyticsService:
    async def track(self, session: AsyncSession, event_name: str, payload: dict, user_id: str | None = None) -> None:
        session.add(AnalyticsEvent(user_id=user_id, event_name=event_name, payload=payload))

    async def product_metrics(self, session: AsyncSession) -> dict[str, int]:
        users = await session.scalar(select(func.count()).select_from(User))
        subscriptions = await session.scalar(
            select(func.count()).select_from(AnalyticsEvent).where(
                AnalyticsEvent.event_name == "subscription_started"
            )
        )
        readings = await session.scalar(
            select(func.count()).select_from(AnalyticsEvent).where(
                AnalyticsEvent.event_name == "tarot_reading_created"
            )
        )
        return {
            "dau": users or 0,
            "mau": users or 0,
            "subscription_conversions": subscriptions or 0,
            "readings": readings or 0,
        }
