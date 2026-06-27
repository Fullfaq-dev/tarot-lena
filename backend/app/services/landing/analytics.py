from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AnalyticsEvent, LandingEvent, LandingSession


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]


async def start_session(
    session: AsyncSession,
    *,
    visitor_id: str,
    page: str = "index",
    referrer: str | None = None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    user_agent: str | None = None,
    device_type: str | None = None,
    screen_width: int | None = None,
    screen_height: int | None = None,
) -> LandingSession:
    row = LandingSession(
        visitor_id=visitor_id[:64],
        page=page[:64] or "index",
        referrer=_truncate(referrer, 2048),
        utm_source=_truncate(utm_source, 128),
        utm_medium=_truncate(utm_medium, 128),
        utm_campaign=_truncate(utm_campaign, 128),
        user_agent=_truncate(user_agent, 512),
        device_type=_truncate(device_type, 32),
        screen_width=screen_width,
        screen_height=screen_height,
    )
    session.add(row)
    await session.flush()
    session.add(
        LandingEvent(
            session_id=row.id,
            event_type="pageview",
            element_label=page[:64] or "index",
        )
    )
    return row


async def record_events(
    session: AsyncSession,
    *,
    session_id: str,
    events: list[dict[str, Any]],
) -> int:
    landing_session = await session.scalar(
        select(LandingSession).where(LandingSession.id == session_id)
    )
    if landing_session is None:
        return 0

    added = 0
    click_delta = 0
    for item in events[:100]:
        event_type = str(item.get("type") or item.get("event_type") or "").strip()[:64]
        if not event_type:
            continue
        session.add(
            LandingEvent(
                session_id=session_id,
                event_type=event_type,
                element_id=_truncate(str(item.get("element_id") or ""), 128) or None,
                element_label=_truncate(str(item.get("element_label") or ""), 255) or None,
                section_id=_truncate(str(item.get("section_id") or ""), 64) or None,
                value=_truncate(str(item.get("value") or ""), 128) or None,
                meta=item.get("meta") if isinstance(item.get("meta"), dict) else {},
            )
        )
        added += 1
        if event_type == "click":
            click_delta += 1

    if click_delta:
        landing_session.click_count = (landing_session.click_count or 0) + click_delta
    return added


async def close_session(
    session: AsyncSession,
    *,
    session_id: str,
    duration_sec: int | None = None,
    max_scroll_pct: int | None = None,
) -> bool:
    landing_session = await session.scalar(
        select(LandingSession).where(LandingSession.id == session_id)
    )
    if landing_session is None:
        return False

    if duration_sec is not None and duration_sec >= 0:
        landing_session.duration_sec = min(duration_sec, 86_400)
    if max_scroll_pct is not None:
        landing_session.max_scroll_pct = max(
            landing_session.max_scroll_pct or 0,
            min(max_scroll_pct, 100),
        )
    landing_session.ended_at = datetime.now(UTC)
    return True


async def landing_stats(session: AsyncSession, *, days: int = 30) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=days)

    sessions_count = await session.scalar(
        select(func.count())
        .select_from(LandingSession)
        .where(LandingSession.created_at >= since)
    ) or 0
    unique_visitors = await session.scalar(
        select(func.count(func.distinct(LandingSession.visitor_id)))
        .select_from(LandingSession)
        .where(LandingSession.created_at >= since)
    ) or 0
    avg_duration = await session.scalar(
        select(func.avg(LandingSession.duration_sec))
        .select_from(LandingSession)
        .where(
            LandingSession.created_at >= since,
            LandingSession.duration_sec.is_not(None),
        )
    )
    avg_scroll = await session.scalar(
        select(func.avg(LandingSession.max_scroll_pct))
        .select_from(LandingSession)
        .where(LandingSession.created_at >= since)
    )
    total_clicks = await session.scalar(
        select(func.count())
        .select_from(LandingEvent)
        .where(
            LandingEvent.created_at >= since,
            LandingEvent.event_type == "click",
        )
    ) or 0
    cta_clicks = await session.scalar(
        select(func.count())
        .select_from(LandingEvent)
        .where(
            LandingEvent.created_at >= since,
            LandingEvent.event_type == "click",
            LandingEvent.element_label.ilike("%telegram%"),
        )
    ) or 0
    bot_conversions = await session.scalar(
        select(func.count())
        .select_from(AnalyticsEvent)
        .where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.event_name.in_(("bot.user_created", "bot.command_start")),
            AnalyticsEvent.payload["start_payload"].as_string() == "landing",
        )
    ) or 0

    daily_day = cast(LandingSession.created_at, Date)
    daily_rows = await session.execute(
        select(
            daily_day.label("day"),
            func.count(LandingSession.id).label("sessions"),
            func.count(func.distinct(LandingSession.visitor_id)).label("unique_visitors"),
        )
        .where(LandingSession.created_at >= since)
        .group_by(daily_day)
        .order_by(daily_day)
    )
    daily = [
        {
            "date": str(row.day),
            "sessions": int(row.sessions or 0),
            "unique_visitors": int(row.unique_visitors or 0),
        }
        for row in daily_rows
    ]

    click_rows = await session.execute(
        select(
            LandingEvent.element_label,
            LandingEvent.element_id,
            LandingEvent.section_id,
            func.count().label("count"),
        )
        .where(
            LandingEvent.created_at >= since,
            LandingEvent.event_type == "click",
        )
        .group_by(LandingEvent.element_label, LandingEvent.element_id, LandingEvent.section_id)
        .order_by(func.count().desc())
        .limit(20)
    )
    top_clicks = [
        {
            "label": row.element_label or row.element_id or "—",
            "element_id": row.element_id,
            "section": row.section_id,
            "count": int(row.count or 0),
        }
        for row in click_rows
    ]

    section_rows = await session.execute(
        select(
            LandingEvent.section_id,
            func.count().label("views"),
        )
        .where(
            LandingEvent.created_at >= since,
            LandingEvent.event_type == "section_view",
            LandingEvent.section_id.is_not(None),
        )
        .group_by(LandingEvent.section_id)
        .order_by(func.count().desc())
    )
    top_sections = [
        {"section_id": row.section_id, "views": int(row.views or 0)}
        for row in section_rows
    ]

    device_rows = await session.execute(
        select(
            LandingSession.device_type,
            func.count().label("sessions"),
        )
        .where(LandingSession.created_at >= since)
        .group_by(LandingSession.device_type)
        .order_by(func.count().desc())
    )
    devices = [
        {"device": row.device_type or "unknown", "sessions": int(row.sessions or 0)}
        for row in device_rows
    ]

    utm_rows = await session.execute(
        select(
            LandingSession.utm_source,
            func.count().label("sessions"),
        )
        .where(
            LandingSession.created_at >= since,
            LandingSession.utm_source.is_not(None),
            LandingSession.utm_source != "",
        )
        .group_by(LandingSession.utm_source)
        .order_by(func.count().desc())
        .limit(10)
    )
    utm_sources = [
        {"source": row.utm_source, "sessions": int(row.sessions or 0)}
        for row in utm_rows
    ]

    recent_rows = await session.scalars(
        select(LandingSession)
        .where(LandingSession.created_at >= since)
        .order_by(LandingSession.created_at.desc())
        .limit(50)
    )
    recent_sessions = [
        {
            "id": row.id,
            "visitor_id": row.visitor_id,
            "page": row.page,
            "device_type": row.device_type,
            "duration_sec": row.duration_sec,
            "max_scroll_pct": row.max_scroll_pct,
            "click_count": row.click_count,
            "utm_source": row.utm_source,
            "referrer": row.referrer,
            "created_at": row.created_at.isoformat(),
        }
        for row in recent_rows
    ]

    conversion_rate = 0.0
    if sessions_count:
        conversion_rate = round((bot_conversions / sessions_count) * 100, 1)

    return {
        "summary": {
            "sessions": int(sessions_count),
            "unique_visitors": int(unique_visitors),
            "avg_duration_sec": int(avg_duration or 0),
            "avg_scroll_pct": int(avg_scroll or 0),
            "total_clicks": int(total_clicks),
            "cta_clicks": int(cta_clicks),
            "bot_conversions": int(bot_conversions),
            "conversion_rate_pct": conversion_rate,
        },
        "daily": daily,
        "top_clicks": top_clicks,
        "top_sections": top_sections,
        "devices": devices,
        "utm_sources": utm_sources,
        "recent_sessions": recent_sessions,
    }
