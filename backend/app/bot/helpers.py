import logging

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_PROCESSING_TEXT = {
    "photo": "🔍 Смотрю на фото и готовлю разбор… Обычно это занимает около минуты.",
    "voice": "🎤 Расшифровываю голосовое…",
}


async def send_processing_placeholder(message: Message, *, kind: str) -> Message | None:
    sticker_id = get_settings().telegram_placeholder_sticker_id.strip()
    if sticker_id:
        try:
            return await message.answer_sticker(sticker_id)
        except Exception as exc:
            logger.warning("Failed to send placeholder sticker: %s", exc)
            return None

    text = _PROCESSING_TEXT.get(kind)
    if not text:
        return None
    return await message.answer(text)


async def delete_message_safe(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except Exception:
        pass


async def clear_processing_placeholder(message: Message | None) -> None:
    await delete_message_safe(message)


async def safe_callback_answer(
    callback: CallbackQuery,
    text: str | None = None,
    *,
    show_alert: bool = False,
) -> None:
    try:
        await callback.answer(text, show_alert=show_alert)
    except TelegramBadRequest as exc:
        if "query is too old" in str(exc).lower() or "query id is invalid" in str(exc).lower():
            return
        raise


async def safe_edit(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    parse_mode: ParseMode | str | None = None,
) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as exc:
        error = str(exc).lower()
        if "message is not modified" in error:
            return
        try:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            logger.exception("safe_edit fallback answer failed")
    except Exception:
        logger.exception("safe_edit failed")
        try:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            logger.exception("safe_edit fallback answer failed")
