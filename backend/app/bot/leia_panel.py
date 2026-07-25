"""Send Leia UI panels as new messages (preserve readings in chat history)."""

from __future__ import annotations

from aiogram.types import CallbackQuery, Message, ReplyMarkupUnion

from app.bot.leia_assets import send_leia_photo
from app.bot.rich_messages import present_rich_panel


async def present_leia_scene(
    message: Message,
    text: str,
    *,
    reply_markup: ReplyMarkupUnion | None = None,
    image_key: str | None = None,
) -> None:
    if image_key:
        await send_leia_photo(message, image_key)
    await present_rich_panel(message, text, reply_markup=reply_markup)


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
