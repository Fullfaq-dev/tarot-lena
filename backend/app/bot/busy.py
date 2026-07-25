"""Per-user lock so only one reading/AI job runs at a time."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_BUSY_TTL_SEC = 180
_KEY = "leia:busy:{tid}"

_redis: Redis | None = None


def _client() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def is_user_busy(telegram_id: int) -> bool:
    try:
        return bool(await _client().exists(_KEY.format(tid=telegram_id)))
    except Exception:
        logger.exception("busy check failed")
        return False


async def try_acquire_busy(telegram_id: int, *, label: str = "reading") -> bool:
    """Return True if lock acquired."""
    try:
        ok = await _client().set(
            _KEY.format(tid=telegram_id),
            label,
            nx=True,
            ex=_BUSY_TTL_SEC,
        )
        return bool(ok)
    except Exception:
        logger.exception("busy acquire failed")
        return True  # fail open so users are not stuck forever


async def release_busy(telegram_id: int) -> None:
    try:
        await _client().delete(_KEY.format(tid=telegram_id))
    except Exception:
        logger.exception("busy release failed")


@asynccontextmanager
async def user_busy_lock(telegram_id: int, *, label: str = "reading") -> AsyncIterator[bool]:
    """Yields True if lock held; False if user already busy."""
    acquired = await try_acquire_busy(telegram_id, label=label)
    try:
        yield acquired
    finally:
        if acquired:
            await release_busy(telegram_id)


BUSY_ALERT = "⏳ Подожди немного — я ещё заканчиваю предыдущий разбор."
BUSY_HINT = "⏳ Я ещё готовлю прошлый разбор. Подожди, пожалуйста — скоро отвечу."
