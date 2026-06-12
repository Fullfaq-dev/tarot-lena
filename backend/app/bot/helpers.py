import logging

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


async def safe_callback_answer(callback: CallbackQuery, text: str | None = None) -> None:
    try:
        await callback.answer(text)
    except TelegramBadRequest as exc:
        if "query is too old" in str(exc).lower() or "query id is invalid" in str(exc).lower():
            return
        raise


async def safe_edit(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        await message.answer(text, reply_markup=reply_markup)
