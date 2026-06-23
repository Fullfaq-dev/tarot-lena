import asyncio
import logging

from aiogram import Bot

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def send_telegram_message(
    telegram_id: int,
    text: str,
    *,
    reply_markup=None,
) -> None:
    settings = get_settings()
    if settings.telegram_bot_token == "replace-me":
        return
    try:
        async with Bot(token=settings.telegram_bot_token) as bot:
            await bot.send_message(
                telegram_id,
                text,
                parse_mode=None,
                reply_markup=reply_markup,
            )
    except Exception as exc:
        logger.warning("Failed to notify telegram_id=%s: %s", telegram_id, exc)


def notify_telegram_message(
    telegram_id: int,
    text: str,
    *,
    reply_markup=None,
) -> None:
    asyncio.create_task(
        send_telegram_message(telegram_id, text, reply_markup=reply_markup)
    )


async def notify_admins(text: str) -> None:
    settings = get_settings()
    for admin_id in settings.admin_ids:
        await send_telegram_message(admin_id, text)
