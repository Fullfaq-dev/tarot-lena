import asyncio
import logging
from pathlib import Path

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def send_bot_html(
    bot: Bot,
    telegram_id: int,
    text: str,
    *,
    reply_markup=None,
) -> bool:
    try:
        await bot.send_message(
            telegram_id,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
        return True
    except Exception as exc:
        logger.warning("Failed to send HTML message to telegram_id=%s: %s", telegram_id, exc)
        return False


async def send_bot_photo(
    bot: Bot,
    telegram_id: int,
    image_path: str,
    *,
    caption_html: str,
    caption_plain: str,
    reply_markup=None,
) -> bool:
    path = Path(image_path)
    if not path.exists():
        return await send_bot_html(bot, telegram_id, caption_plain, reply_markup=reply_markup)
    photo = FSInputFile(path)
    try:
        await bot.send_photo(
            telegram_id,
            photo,
            caption=caption_html[:1024],
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
        return True
    except Exception:
        try:
            await bot.send_photo(
                telegram_id,
                photo,
                caption=caption_plain[:1024],
                parse_mode=None,
                reply_markup=reply_markup,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to send photo to telegram_id=%s: %s", telegram_id, exc)
            return False


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


async def notify_owner(text: str, *, bot: Bot | None = None) -> None:
    """Send a private notification only to the configured owner."""
    settings = get_settings()
    owner_id = settings.owner_telegram_id
    if not owner_id:
        return
    if bot is not None:
        try:
            await bot.send_message(owner_id, text)
            return
        except Exception as exc:
            logger.warning("notify_owner via bot failed: %s", exc)
    await send_telegram_message(owner_id, text)
