from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.services.landing import analytics as landing_analytics

router = APIRouter(tags=["landing-analytics"])


class StartSessionBody(BaseModel):
    visitor_id: str = Field(min_length=8, max_length=64)
    page: str = Field(default="index", max_length=64)
    referrer: str | None = Field(default=None, max_length=2048)
    utm_source: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)
    device_type: str | None = Field(default=None, max_length=32)
    screen_width: int | None = Field(default=None, ge=0, le=10000)
    screen_height: int | None = Field(default=None, ge=0, le=10000)


class EventsBody(BaseModel):
    session_id: str
    events: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


class CloseSessionBody(BaseModel):
    session_id: str
    duration_sec: int | None = Field(default=None, ge=0, le=86_400)
    max_scroll_pct: int | None = Field(default=None, ge=0, le=100)


@router.post("/session")
async def start_session(
    body: StartSessionBody,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user_agent = request.headers.get("user-agent")
    row = await landing_analytics.start_session(
        session,
        visitor_id=body.visitor_id,
        page=body.page,
        referrer=body.referrer,
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
        user_agent=user_agent,
        device_type=body.device_type,
        screen_width=body.screen_width,
        screen_height=body.screen_height,
    )
    await session.commit()
    return {"session_id": row.id}


@router.post("/events")
async def record_events(
    body: EventsBody,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int | bool]:
    added = await landing_analytics.record_events(
        session,
        session_id=body.session_id,
        events=body.events,
    )
    await session.commit()
    return {"ok": True, "added": added}


@router.post("/session/close")
async def close_session(
    body: CloseSessionBody,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    ok = await landing_analytics.close_session(
        session,
        session_id=body.session_id,
        duration_sec=body.duration_sec,
        max_scroll_pct=body.max_scroll_pct,
    )
    await session.commit()
    return {"ok": ok}
