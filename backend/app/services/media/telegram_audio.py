import uuid
from pathlib import Path

from aiogram import Bot

from app.core.config import get_settings
from app.services.media.stored_file import StoredFile


async def store_telegram_file(
    bot: Bot,
    file_id: str,
    *,
    default_ext: str = ".ogg",
) -> StoredFile:
    settings = get_settings()
    tg_file = await bot.get_file(file_id)
    if tg_file.file_path is None:
        raise ValueError("Не удалось получить файл из Telegram")

    ext = Path(tg_file.file_path).suffix or default_ext
    filename = f"{uuid.uuid4().hex}{ext}"
    dest_dir = settings.media_storage_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    await bot.download_file(tg_file.file_path, dest)
    public_url = f"{settings.public_base_url.rstrip('/')}/static/generated/{filename}"
    return StoredFile(path=dest, public_url=public_url)


async def store_telegram_voice(bot: Bot, file_id: str) -> StoredFile:
    return await store_telegram_file(bot, file_id, default_ext=".ogg")
