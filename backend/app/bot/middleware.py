from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TelegramUser

from app.services.locale.service import LocaleService

logger = logging.getLogger(__name__)


class LocaleSyncMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: TelegramUser | None = data.get("event_from_user")
        if user is None:
            user = getattr(event, "from_user", None)
        if user is not None:
            try:
                data["ui_language"] = await LocaleService().sync_from_telegram(user)
            except Exception:
                logger.exception("locale sync failed for telegram_id=%s", user.id)
        return await handler(event, data)
