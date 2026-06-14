from pathlib import Path

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto, Message

from app.bot.media import truncate_caption
from app.bot.rich_layouts import format_tarot_collage, format_tarot_reading_rich, tarot_collage_available
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
    if tarot_collage_available() and format_tarot_collage(cards):
        rich_with_collage = format_tarot_reading_rich(
            label=label,
            question=question,
            cards=cards,
            reading_type=reading_type,
            interpretation=interpretation,
            lang=lang,
            include_collage=True,
        )
        try:
            await send_rich_message(
                message.bot,
                message.chat.id,
                rich_with_collage,
                reply_markup=reply_markup,
                message_thread_id=message.message_thread_id,
            )
            return
        except TelegramBadRequest:
            pass

    rich_text = format_tarot_reading_rich(
        label=label,
        question=question,
        cards=cards,
        reading_type=reading_type,
        interpretation=interpretation,
        lang=lang,
        include_collage=False,
    )
    await send_drawn_cards(message, cards)
    await answer_rich_message(message, rich_text, reply_markup=reply_markup)
