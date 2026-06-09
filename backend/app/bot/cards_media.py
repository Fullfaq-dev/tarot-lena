from aiogram.types import FSInputFile, InputMediaPhoto, Message

from app.core.config import get_settings


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
