from typing import Any

from app.database.models import AnalyticsEvent
from app.database.session import AsyncSessionLocal


async def track_event(
    event_name: str,
    user_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        session.add(
            AnalyticsEvent(
                user_id=user_id,
                event_name=event_name,
                payload=payload or {},
            )
        )
        await session.commit()
