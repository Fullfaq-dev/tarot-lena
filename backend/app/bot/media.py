import logging

import httpx
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, Message

logger = logging.getLogger(__name__)

TELEGRAM_CAPTION_LIMIT = 1024


def truncate_caption(text: str, limit: int = TELEGRAM_CAPTION_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


async def send_photo_from_url(
    message: Message,
    url: str,
    *,
    caption: str | None = None,
    caption_plain: str | None = None,
    parse_mode: ParseMode | None = None,
    reply_markup=None,
) -> bool:
    try:
        async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            ext = ".png" if "png" in content_type else ".jpg"
            photo = BufferedInputFile(response.content, filename=f"image{ext}")
            if caption:
                caption = truncate_caption(caption)
            try:
                await message.answer_photo(
                    photo,
                    caption=caption,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            except TelegramBadRequest as exc:
                if parse_mode and caption_plain:
                    await message.answer_photo(
                        photo,
                        caption=truncate_caption(caption_plain),
                        parse_mode=None,
                        reply_markup=reply_markup,
                    )
                else:
                    raise exc
            return True
    except Exception as exc:
        logger.warning("Failed to download/send photo url=%s: %s", url, exc)
        return False
