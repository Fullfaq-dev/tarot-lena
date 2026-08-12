"""Persist user↔bot dialog turns for the admin chat timeline."""

from __future__ import annotations

import logging
from typing import Any

from app.database.models import Message, MessageRole
from app.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def log_dialog_message(
    user_id: str,
    role: str,
    content: str,
    *,
    meta: dict[str, Any] | None = None,
    telegram_message_id: int | None = None,
) -> str | None:
    text = (content or "").strip()
    if not user_id or not text:
        return None
    try:
        async with AsyncSessionLocal() as session:
            row = Message(
                user_id=user_id,
                role=role,
                content=text[:20000],
                telegram_message_id=telegram_message_id,
                meta=meta or {},
            )
            session.add(row)
            await session.commit()
            return row.id
    except Exception:
        logger.exception("Failed to log dialog message user_id=%s role=%s", user_id, role)
        return None


async def log_dialog_exchange(
    user_id: str,
    user_text: str,
    assistant_text: str,
    *,
    source: str,
    extra_meta: dict[str, Any] | None = None,
) -> None:
    base = {"source": source, **(extra_meta or {})}
    await log_dialog_message(
        user_id,
        MessageRole.USER.value,
        user_text,
        meta={**base, "exchange": True},
    )
    await log_dialog_message(
        user_id,
        MessageRole.ASSISTANT.value,
        assistant_text,
        meta={**base, "exchange": True},
    )
