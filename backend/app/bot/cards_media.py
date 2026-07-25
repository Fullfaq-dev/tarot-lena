from pathlib import Path

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto, Message

from app.bot.media import truncate_caption
from app.bot.rich_layouts import format_tarot_collage, format_tarot_reading_rich, tarot_collage_available
from app.bot.formatting import leia_markdown_to_html, to_telegram_html
from app.bot.rich_messages import answer_rich_message, send_rich_message
from app.core.config import get_settings


def _card_image_path(card: dict) -> Path | None:
    settings = get_settings()
    candidates: list[Path] = []
    if card.get("image_file"):
        candidates.append(settings.tarot_cards_dir / str(card["image_file"]))
    if card.get("image_path"):
        candidates.append(Path(str(card["image_path"])))
        candidates.append(settings.tarot_cards_dir / Path(str(card["image_path"])).name)
    for path in candidates:
        if path.exists():
            return path
    return None


async def send_card_with_caption(
    message: Message,
    card: dict,
    *,
    caption_html: str,
    caption_plain: str,
    reply_markup=None,
) -> bool:
    path = _card_image_path(card)
    if path is None:
        return False

    photo = FSInputFile(path)
    html = truncate_caption(caption_html)
    plain = truncate_caption(caption_plain)
    try:
        await message.answer_photo(
            photo,
            caption=html,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
        return True
    except TelegramBadRequest:
        try:
            await message.answer_photo(
                photo,
                caption=plain,
                parse_mode=None,
                reply_markup=reply_markup,
            )
            return True
        except TelegramBadRequest:
            return False


async def send_drawn_cards(message: Message, cards: list[dict]) -> None:
    media: list[InputMediaPhoto] = []
    for card in cards:
        path = _card_image_path(card)
        if path is None:
            continue
        media.append(InputMediaPhoto(media=FSInputFile(path), caption=str(card["name"])))

    if not media:
        return
    if len(media) == 1:
        await message.answer_photo(media[0].media, caption=media[0].caption)
        return
    await message.answer_media_group(media[:10])


async def send_tarot_reading_rich(
    message: Message,
    *,
    label: str,
    question: str,
    reading_type: str,
    cards: list[dict],
    interpretation: str,
    lang: str,
    reply_markup=None,
) -> None:
    """Cards/collage first, full interpretation in a separate rich message (Telegram drops long tails)."""
    interpretation = (interpretation or "").strip()
    header = format_tarot_reading_rich(
        label=label,
        question=question,
        cards=cards,
        reading_type=reading_type,
        interpretation="",
        lang=lang,
        include_collage=True,
    )

    header_sent = False
    if header.strip():
        try:
            await send_rich_message(
                message.bot,
                message.chat.id,
                header,
                reply_markup=None,
                message_thread_id=message.message_thread_id,
            )
            header_sent = True
        except TelegramBadRequest:
            header_sent = False

    if not header_sent:
        await send_drawn_cards(message, cards)
        if question:
            caption = leia_markdown_to_html(f"**{label}**\n\n**Вопрос:** {question}")
            await message.answer(caption, parse_mode="HTML")

    if interpretation:
        await answer_rich_message(message, interpretation, reply_markup=reply_markup)
    elif reply_markup is not None:
        await message.answer(
            "Карты на месте — полная расшифровка не пришла. "
            "Напиши «Расшифруй» или задай вопрос к раскладу.",
            reply_markup=reply_markup,
        )
