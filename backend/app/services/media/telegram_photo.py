import uuid
from pathlib import Path

from aiogram import Bot

from app.core.config import get_settings


async def store_telegram_photo(bot: Bot, file_id: str) -> str:
    """Скачивает фото из Telegram и возвращает публичный URL для KIE."""
    settings = get_settings()
    tg_file = await bot.get_file(file_id)
    if tg_file.file_path is None:
        raise ValueError("Не удалось получить файл из Telegram")

    ext = Path(tg_file.file_path).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest_dir = settings.media_storage_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    await bot.download_file(tg_file.file_path, dest)
    return f"{settings.public_base_url.rstrip('/')}/static/generated/{filename}"
