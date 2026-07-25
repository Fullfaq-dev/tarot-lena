import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.busy import BUSY_ALERT, BUSY_HINT, user_busy_lock
from app.bot.streaming import typing_loop
from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

_PROCESSING_TEXT = {
    "photo": "🔍 Смотрю на фото и готовлю разбор… Обычно это занимает около минуты.",
    "voice": "🎤 Расшифровываю голосовое…",
}


async def with_typing(message: Message, coro: Awaitable[T]) -> T:
    """Keep Telegram «печатает…» visible while awaiting AI / heavy work."""
    stop = asyncio.Event()
    task = asyncio.create_task(typing_loop(message.bot, message.chat.id, stop))
    try:
        try:
            await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        except Exception:
            pass
        return await coro
    finally:
        stop.set()
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except Exception:
            task.cancel()


async def _edit_status(status: Message | None, text: str) -> None:
    if status is None:
        return
    try:
        await status.edit_text(text)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            logger.debug("status edit skipped: %s", exc)
    except Exception:
        logger.debug("status edit failed", exc_info=True)


async def run_busy_job(
    message: Message,
    coro_factory: Callable[[], Awaitable[T]],
    *,
    loading_text: str = "✨ Секунду, смотрю карты и числа…",
    progress_text: str = "🔮 Ещё думаю… обычно это занимает до минуты",
    telegram_id: int | None = None,
    label: str = "reading",
) -> T | None:
    """Acquire busy lock, show status + typing, run job, cleanup.

    Returns None if the user is already busy.
    ``coro_factory`` must create a fresh awaitable (not a reused coroutine).
    """
    tid = telegram_id
    if tid is None and message.from_user is not None:
        tid = message.from_user.id
    if tid is None:
        tid = message.chat.id

    async with user_busy_lock(tid, label=label) as acquired:
        if not acquired:
            await message.answer(BUSY_HINT)
            return None

        status = await message.answer(loading_text)
        stop = asyncio.Event()
        typing_task = asyncio.create_task(
            typing_loop(message.bot, message.chat.id, stop)
        )
        progress_task: asyncio.Task | None = None

        async def _progress() -> None:
            # Visible heartbeat so wait never feels "frozen".
            await asyncio.sleep(6)
            if not stop.is_set():
                await _edit_status(status, progress_text)
            await asyncio.sleep(12)
            if not stop.is_set():
                await _edit_status(
                    status, "⏳ Ещё чуть-чуть… обычно это до минуты"
                )

        try:
            try:
                await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
            except Exception:
                pass
            progress_task = asyncio.create_task(_progress())
            return await coro_factory()
        finally:
            stop.set()
            if progress_task is not None:
                progress_task.cancel()
            try:
                await asyncio.wait_for(typing_task, timeout=1.0)
            except Exception:
                typing_task.cancel()
            await delete_message_safe(status)


async def refuse_if_busy_callback(callback: CallbackQuery) -> bool:
    """If user is busy, answer alert and return True (caller should return)."""
    from app.bot.busy import is_user_busy

    if await is_user_busy(callback.from_user.id):
        await safe_callback_answer(callback, BUSY_ALERT, show_alert=True)
        return True
    return False


async def refuse_if_busy_message(message: Message) -> bool:
    from app.bot.busy import is_user_busy

    tid = message.from_user.id if message.from_user else message.chat.id
    if await is_user_busy(tid):
        await message.answer(BUSY_HINT)
        return True
    return False


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
