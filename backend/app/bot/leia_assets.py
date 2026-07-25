"""Static images from client spec (Асторобот.docx)."""

from __future__ import annotations

from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message, ReplyMarkupUnion

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "leia"

# Content images from docx (screenshots in «Правки» are excluded).
PRODUCT_IMAGES: dict[str, str] = {
    "love": "image5.jpg",
    "forecast": "image9.jpg",
    "wealth": "image10.jpg",
    "negative": "image2.jpg",
    "question": "image8.jpg",
    "tarot_spread": "image11.png",
}

SCENE_IMAGES: dict[str, str] = {
    "portrait": "image7.jpg",
    "packages": "image1.jpg",
    "referral": "image3.jpg",
    "funnel_day2": "image4.jpg",
    "no_purchase": "image4.jpg",
}


def leia_asset_path(key: str) -> Path | None:
    filename = PRODUCT_IMAGES.get(key) or SCENE_IMAGES.get(key)
    if not filename:
        return None
    path = ASSETS_DIR / filename
    return path if path.is_file() else None


async def send_leia_photo(
    message: Message,
    key: str,
    *,
    caption: str | None = None,
    reply_markup: ReplyMarkupUnion | None = None,
) -> bool:
    path = leia_asset_path(key)
    if path is None:
        return False
    photo = FSInputFile(path)
    try:
        await message.answer_photo(
            photo,
            caption=caption,
            reply_markup=reply_markup,
        )
        return True
    except TelegramBadRequest:
        try:
            await message.answer_photo(
                photo,
                caption=caption,
                parse_mode=None,
                reply_markup=reply_markup,
            )
            return True
        except TelegramBadRequest:
            return False
