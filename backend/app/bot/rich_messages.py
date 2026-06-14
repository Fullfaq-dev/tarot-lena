"""Send and stream Telegram rich messages with legacy HTML fallback."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ChatIdUnion, Message, ReplyMarkupUnion, ReplyParameters

from app.bot.formatting import prepare_rich_markdown, to_telegram_html
from app.bot.telegram_rich import InputRichMessage, SendRichMessage, SendRichMessageDraft

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

TELEGRAM_RICH_MESSAGE_LIMIT = 32768
TELEGRAM_MESSAGE_LIMIT = 4096

_UNSUPPORTED_RICH_MARKERS = (
    "method not found",
    "not found",
    "unknown method",
    "rich message",
    "rich_message",
)


def truncate_rich_text(text: str, limit: int = TELEGRAM_RICH_MESSAGE_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def truncate_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def rich_draft_id(chat_id: int, anchor_message_id: int | None = None) -> int:
    seed = anchor_message_id or 1
    draft_id = (chat_id * 1_000_003 + seed * 97) % (2**31 - 1)
    return draft_id or 1


def is_rich_message_unsupported(exc: Exception) -> bool:
    err = str(exc).lower()
    return any(marker in err for marker in _UNSUPPORTED_RICH_MARKERS)


def is_parse_entities_error(exc: TelegramBadRequest) -> bool:
    err = str(exc).lower()
    return "can't parse entities" in err or "parse entities" in err


def _input_rich_message(text: str) -> InputRichMessage:
    markdown = truncate_rich_text(prepare_rich_markdown(text))
    return InputRichMessage(markdown=markdown)


async def send_rich_message(
    bot: Bot,
    chat_id: ChatIdUnion,
    text: str,
    *,
    reply_markup: ReplyMarkupUnion | None = None,
    reply_parameters: ReplyParameters | None = None,
    message_thread_id: int | None = None,
) -> Message:
    return await bot(
        SendRichMessage(
            chat_id=chat_id,
            rich_message=_input_rich_message(text),
            reply_markup=reply_markup,
            reply_parameters=reply_parameters,
            message_thread_id=message_thread_id,
        )
    )


async def send_rich_message_draft(
    bot: Bot,
    chat_id: int,
    draft_id: int,
    text: str,
    *,
    message_thread_id: int | None = None,
) -> bool:
    return await bot(
        SendRichMessageDraft(
            chat_id=chat_id,
            draft_id=draft_id,
            rich_message=_input_rich_message(text),
            message_thread_id=message_thread_id,
        )
    )


async def answer_rich_message(
    message: Message,
    text: str,
    *,
    reply_markup: ReplyMarkupUnion | None = None,
    reply_parameters: ReplyParameters | None = None,
) -> Message | None:
    if not text.strip():
        return None
    try:
        return await send_rich_message(
            message.bot,
            message.chat.id,
            text,
            reply_markup=reply_markup,
            reply_parameters=reply_parameters,
            message_thread_id=message.message_thread_id,
        )
    except TelegramBadRequest as exc:
        if not is_rich_message_unsupported(exc) and not is_parse_entities_error(exc):
            logger.warning("Rich message send failed: %s", exc)
        return await _answer_legacy_html(message, text, reply_markup=reply_markup)


async def edit_or_answer_rich_message(
    message: Message,
    text: str,
    *,
    edit: bool,
    reply_markup: ReplyMarkupUnion | None = None,
) -> Message | None:
    if edit:
        try:
            return await send_rich_message(
                message.bot,
                message.chat.id,
                text,
                reply_markup=reply_markup,
                message_thread_id=message.message_thread_id,
            )
        except TelegramBadRequest as exc:
            if not is_rich_message_unsupported(exc) and not is_parse_entities_error(exc):
                logger.warning("Rich message finalize failed: %s", exc)
            await _send_legacy_formatted(message, text, edit=True, reply_markup=reply_markup)
            return None
    return await answer_rich_message(message, text, reply_markup=reply_markup)


async def _answer_legacy_html(
    message: Message,
    text: str,
    *,
    reply_markup: ReplyMarkupUnion | None = None,
) -> Message:
    body = truncate_text(text)
    html = truncate_text(to_telegram_html(body))
    try:
        return await message.answer(html, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if is_parse_entities_error(exc):
            return await message.answer(body, parse_mode=None, reply_markup=reply_markup)
        raise


async def _send_legacy_formatted(
    message: Message,
    text: str,
    *,
    edit: bool,
    reply_markup: ReplyMarkupUnion | None = None,
) -> None:
    if not text.strip():
        return
    plain = truncate_text(text)
    html = truncate_text(to_telegram_html(text))

    for payload, mode in ((html, ParseMode.HTML), (plain, None)):
        try:
            if edit:
                await message.edit_text(payload, parse_mode=mode, reply_markup=reply_markup)
            else:
                await message.answer(payload, parse_mode=mode, reply_markup=reply_markup)
            return
        except TelegramBadRequest as exc:
            if edit and "message is not modified" in str(exc).lower():
                return
            if mode is ParseMode.HTML and is_parse_entities_error(exc):
                continue
            if mode is None:
                logger.warning("Failed to send legacy formatted text: %s", exc)
                return
