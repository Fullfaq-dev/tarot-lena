import logging

import httpx
from aiogram.types import BufferedInputFile, Message

logger = logging.getLogger(__name__)


async def send_photo_from_url(
    message: Message,
    url: str,
    *,
    caption: str | None = None,
    reply_markup=None,
) -> bool:
    try:
        async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            ext = ".png" if "png" in content_type else ".jpg"
            photo = BufferedInputFile(response.content, filename=f"image{ext}")
            await message.answer_photo(photo, caption=caption, reply_markup=reply_markup)
            return True
    except Exception as exc:
        logger.warning("Failed to download/send photo url=%s: %s", url, exc)
        return False
