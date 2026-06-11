import logging
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.media.audio_convert import ensure_mp3

logger = logging.getLogger(__name__)


class Stt302Client:
    """Synchronous speech-to-text via 302.AI Whisper API."""

    async def transcribe_file(self, audio_path: Path, *, language: str = "ru") -> str:
        settings = get_settings()
        api_key = settings.ai302_api_key.strip()
        if not api_key or api_key == "replace-me":
            raise ValueError("302.AI API key не настроен")

        path = await ensure_mp3(audio_path)
        if not path.exists() or path.stat().st_size == 0:
            raise ValueError("Пустой аудиофайл")

        url = f"{settings.ai302_base_url.rstrip('/')}/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}
        mime = "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/ogg"
        data = {
            "model": settings.ai302_stt_model,
            "language": language,
            "response_format": "json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            with path.open("rb") as handle:
                response = await client.post(
                    url,
                    headers=headers,
                    data=data,
                    files={"file": (path.name, handle, mime)},
                )

        if response.status_code >= 400:
            detail = response.text.strip()[:300]
            logger.warning("302.AI STT failed status=%s body=%s", response.status_code, detail)
            raise ValueError(f"302.AI STT: {detail or response.status_code}")

        body = response.json()
        text = body.get("text") if isinstance(body, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise ValueError("302.AI не вернул текст расшифровки")
        return text.strip()
