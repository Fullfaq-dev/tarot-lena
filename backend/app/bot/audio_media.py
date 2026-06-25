import logging

from aiogram.types import BufferedInputFile, Message

from app.core.http import get_async_client

logger = logging.getLogger(__name__)


async def send_voice_from_url(message: Message, url: str) -> bool:
    try:
        client = get_async_client()
        response = await client.get(url, timeout=90)
        response.raise_for_status()
        content_type = (response.headers.get("content-type") or "").lower()
        ext = ".mp3" if "mpeg" in content_type or "mp3" in content_type else ".ogg"
        voice = BufferedInputFile(response.content, filename=f"reply{ext}")
        await message.answer_voice(voice)
        return True
    except Exception as exc:
        logger.warning("Failed to download/send voice url=%s: %s", url, exc)
        return False
