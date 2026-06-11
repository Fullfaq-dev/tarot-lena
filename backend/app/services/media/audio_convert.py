import asyncio
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


async def ensure_mp3(path: Path) -> Path:
    """Convert Telegram voice (ogg/opus) to mp3 for reliable KIE STT."""
    if path.suffix.lower() == ".mp3":
        return path
    if not shutil.which("ffmpeg"):
        logger.warning("ffmpeg not found, using original audio format for STT")
        return path

    dest = path.with_suffix(".mp3")
    if dest.exists() and dest.stat().st_size > 0 and dest.stat().st_mtime >= path.stat().st_mtime:
        return dest

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "4",
        str(dest),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    if proc.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
        return dest
    logger.warning("ffmpeg conversion failed, using original audio for STT")
    return path
