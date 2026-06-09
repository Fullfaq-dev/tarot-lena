from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto, Message

from app.bot.media import truncate_caption
from app.core.config import get_settings


async def send_card_with_caption(
    message: Message,
    card: dict,
    *,
    caption_html: str,
    caption_plain: str,
    reply_markup=None,
) -> bool:
    settings = get_settings()
    path = settings.tarot_cards_dir / str(card["image_file"])
    if not path.exists():
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
    settings = get_settings()
    media: list[InputMediaPhoto] = []
    for card in cards:
        path = settings.tarot_cards_dir / str(card["image_file"])
        if not path.exists():
            continue
        media.append(InputMediaPhoto(media=FSInputFile(path), caption=str(card["name"])))

    if not media:
        return
    if len(media) == 1:
        await message.answer_photo(media[0].media, caption=media[0].caption)
        return
    await message.answer_media_group(media[:10])
