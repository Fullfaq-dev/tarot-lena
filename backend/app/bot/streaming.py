import asyncio
import time
from collections.abc import AsyncIterator

from aiogram import Bot
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from app.bot.formatting import to_telegram_html

TELEGRAM_MESSAGE_LIMIT = 4096


def truncate_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


async def typing_loop(bot: Bot, chat_id: int, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except TimeoutError:
            continue


async def _send_formatted_text(message: Message, text: str, *, edit: bool) -> None:
    if not text.strip():
        return
    html = to_telegram_html(text)
    payload = truncate_text(html)
    try:
        if edit:
            await message.edit_text(payload, parse_mode=ParseMode.HTML)
        else:
            await message.answer(payload, parse_mode=ParseMode.HTML)
    except TelegramBadRequest as exc:
        if edit and "message is not modified" in str(exc).lower():
            return
        plain = truncate_text(text)
        try:
            if edit:
                await message.edit_text(plain, parse_mode=None)
            else:
                await message.answer(plain, parse_mode=None)
        except TelegramBadRequest:
            pass


async def stream_to_message(
    anchor: Message,
    chunks: AsyncIterator[str],
    *,
    prefix: str = "",
    min_edit_interval: float = 0.45,
) -> str:
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(anchor.bot, anchor.chat.id, stop_typing))

    sent: Message | None = None
    full = ""
    last_edit = 0.0
    try:
        async for chunk in chunks:
            full += chunk
            if not full.strip():
                continue
            now = time.monotonic()
            body = f"{prefix}{full}"
            if sent is None:
                sent = await anchor.answer(truncate_text(body), parse_mode=None)
                last_edit = now
            elif now - last_edit >= min_edit_interval:
                try:
                    await sent.edit_text(truncate_text(body), parse_mode=None)
                except TelegramBadRequest as exc:
                    if "message is not modified" not in str(exc).lower():
                        pass
                last_edit = now
    finally:
        stop_typing.set()
        await typing_task

    final = full.strip() or "Не удалось получить ответ. Попробуй ещё раз."
    body = f"{prefix}{final}"
    if sent is None:
        await _send_formatted_text(anchor, body, edit=False)
    else:
        await _send_formatted_text(sent, body, edit=True)
    return final
