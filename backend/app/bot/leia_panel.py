"""Send Leia UI panels as new messages (preserve readings in chat history)."""

from __future__ import annotations

from aiogram.types import CallbackQuery, Message, ReplyMarkupUnion

from app.bot.leia_assets import (
    leia_image_rich_available,
    prepend_leia_image,
    send_leia_photo,
)
from app.bot.rich_messages import answer_rich_message, present_rich_text


async def answer_leia_rich(
    message: Message,
    text: str,
    *,
    reply_markup: ReplyMarkupUnion | None = None,
    image_key: str | None = None,
) -> None:
    """One rich message with an embedded hero image when public URLs are configured."""
    body = prepend_leia_image(text, image_key)
    if image_key and not leia_image_rich_available():
        await send_leia_photo(message, image_key)
    await answer_rich_message(message, body, reply_markup=reply_markup)


async def present_leia_scene(
    message: Message,
    text: str,
    *,
    reply_markup: ReplyMarkupUnion | None = None,
    image_key: str | None = None,
) -> None:
    body = prepend_leia_image(text, image_key)
    if image_key and not leia_image_rich_available():
        await send_leia_photo(message, image_key)
    await present_rich_text(message, body, reply_markup=reply_markup)


async def callback_leia_scene(
    callback: CallbackQuery,
    text: str,
    *,
    reply_markup: ReplyMarkupUnion | None = None,
    image_key: str | None = None,
) -> None:
    """Always append a new panel — never edit the message the user clicked."""
    if callback.message is None:
        return
    await present_leia_scene(
        callback.message,
        text,
        reply_markup=reply_markup,
        image_key=image_key,
    )
