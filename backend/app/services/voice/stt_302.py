import logging
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.media.audio_convert import ensure_mp3

logger = logging.getLogger(__name__)

_STT_MODEL_FALLBACKS = ("whisper-1",)


class Stt302Client:
    """Synchronous speech-to-text via 302.AI Whisper API."""

    async def transcribe_file(self, audio_path: Path, *, language: str = "ru") -> str:
        settings = get_settings()
        api_key = settings.ai302_api_key.strip().strip('"').strip("'")
        if not api_key or api_key == "replace-me":
            raise ValueError("302.AI API key не настроен")

        path = await ensure_mp3(audio_path)
        if not path.exists() or path.stat().st_size == 0:
            raise ValueError("Пустой аудиофайл")

        url = f"{settings.ai302_base_url.rstrip('/')}/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        mime = "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/ogg"
        file_bytes = path.read_bytes()

        models = [settings.ai302_stt_model.strip()] if settings.ai302_stt_model.strip() else []
        for model in _STT_MODEL_FALLBACKS:
            if model not in models:
                models.append(model)

        last_error: Exception | None = None
        for model in models:
            multipart: list[tuple[str, tuple[str | None, bytes | str, str | None]]] = [
                ("file", (path.name, file_bytes, mime)),
                ("model", (None, model)),
            ]

            logger.info(
                "302.AI STT request model=%s file=%s bytes=%s",
                model,
                path.name,
                len(file_bytes),
            )

            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(url, headers=headers, files=multipart)
            except Exception as exc:
                last_error = exc
                logger.warning("302.AI STT transport error model=%s: %s", model, exc)
                continue

            if response.status_code >= 400:
                detail = response.text.strip()[:500]
                logger.warning(
                    "302.AI STT failed model=%s status=%s body=%s",
                    model,
                    response.status_code,
                    detail,
                )
                last_error = ValueError(f"302.AI STT: {detail or response.status_code}")
                continue

            body = response.json()
            text = body.get("text") if isinstance(body, dict) else None
            if isinstance(text, str) and text.strip():
                logger.info("302.AI STT ok model=%s chars=%s", model, len(text.strip()))
                return text.strip()

            last_error = ValueError("302.AI не вернул текст расшифровки")

        raise last_error or ValueError("302.AI STT failed")
