import asyncio
import logging
import time
from collections.abc import AsyncIterator

from aiogram import Bot
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from app.bot.formatting import to_telegram_html
from app.bot.rich_messages import (
    edit_or_answer_rich_message,
    is_parse_entities_error,
    is_rich_message_unsupported,
    rich_draft_id,
    send_rich_message_draft,
    truncate_rich_text,
    truncate_text,
)

logger = logging.getLogger(__name__)

DEFAULT_MIN_EDIT_INTERVAL = 2.0


async def chat_action_loop(
    bot: Bot,
    chat_id: int,
    action: ChatAction,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        await bot.send_chat_action(chat_id, action)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except TimeoutError:
            continue


async def typing_loop(bot: Bot, chat_id: int, stop_event: asyncio.Event) -> None:
    await chat_action_loop(bot, chat_id, ChatAction.TYPING, stop_event)


async def _send_formatted_text(message: Message, text: str, *, edit: bool) -> None:
    if not text.strip():
        return
    plain = truncate_text(text)
    html = truncate_text(to_telegram_html(text))

    for payload, mode in ((html, ParseMode.HTML), (plain, None)):
        try:
            if edit:
                await message.edit_text(payload, parse_mode=mode)
            else:
                await message.answer(payload, parse_mode=mode)
            return
        except TelegramBadRequest as exc:
            if edit and "message is not modified" in str(exc).lower():
                return
            if mode is ParseMode.HTML and is_parse_entities_error(exc):
                continue
            if mode is None:
                logger.warning("Failed to send formatted text: %s", exc)
                return


async def stream_to_message(
    anchor: Message,
    chunks: AsyncIterator[str],
    *,
    prefix: str = "",
    min_edit_interval: float = DEFAULT_MIN_EDIT_INTERVAL,
) -> str:
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(anchor.bot, anchor.chat.id, stop_typing))

    sent: Message | None = None
    full = ""
    last_edit = 0.0
    rich_mode = anchor.chat.type == "private"
    rich_draft: int | None = rich_draft_id(anchor.chat.id, anchor.message_id) if rich_mode else None

    try:
        async for chunk in chunks:
            full += chunk
            if not full.strip():
                continue
            now = time.monotonic()
            body = truncate_rich_text(f"{prefix}{full}")

            if rich_mode and rich_draft is not None and (sent is not None or now - last_edit >= min_edit_interval):
                try:
                    await send_rich_message_draft(
                        anchor.bot,
                        anchor.chat.id,
                        rich_draft,
                        body,
                        message_thread_id=anchor.message_thread_id,
                    )
                    last_edit = now
                    continue
                except TelegramBadRequest as exc:
                    if is_rich_message_unsupported(exc):
                        rich_mode = False
                        logger.info("Rich message draft unsupported, falling back to plain streaming")
                    elif now - last_edit < min_edit_interval:
                        continue
                    elif "too many requests" in str(exc).lower() or "retry after" in str(exc).lower():
                        await asyncio.sleep(3.0)
                        continue
                    else:
                        rich_mode = False
                        logger.warning("Rich message draft failed: %s", exc)

            if now - last_edit < min_edit_interval and sent is not None:
                continue

            plain_body = truncate_text(f"{prefix}{full}")
            if sent is None:
                sent = await anchor.answer(plain_body, parse_mode=None)
                last_edit = now
            else:
                try:
                    await sent.edit_text(plain_body, parse_mode=None)
                    last_edit = now
                except TelegramBadRequest as exc:
                    err = str(exc).lower()
                    if "message is not modified" in err:
                        last_edit = now
                    elif "too many requests" in err or "retry after" in err:
                        await asyncio.sleep(3.0)
                    else:
                        last_edit = now
    finally:
        stop_typing.set()
        await typing_task

    final = full.strip() or "Не удалось получить ответ. Попробуй ещё раз."
    body = truncate_rich_text(f"{prefix}{final}")

    if rich_mode:
        try:
            await edit_or_answer_rich_message(anchor, body, edit=False)
            return final
        except TelegramBadRequest as exc:
            if not is_rich_message_unsupported(exc):
                logger.warning("Rich message finalize failed: %s", exc)

    if sent is None:
        await _send_formatted_text(anchor, truncate_text(f"{prefix}{final}"), edit=False)
    else:
        await _send_formatted_text(sent, truncate_text(f"{prefix}{final}"), edit=True)
    return final
