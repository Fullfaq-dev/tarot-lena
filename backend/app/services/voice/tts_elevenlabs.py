import logging
import uuid

from app.core.config import get_settings
from app.core.http import get_async_client

logger = logging.getLogger(__name__)


async def synthesize_to_public_url(text: str, voice_id: str) -> str:
    settings = get_settings()
    api_key = settings.elevenlabs_api_key.strip()
    if not api_key or api_key == "replace-me":
        raise RuntimeError("ElevenLabs API key is not configured")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": settings.elevenlabs_tts_model,
        "language_code": "ru",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "speed": 1.0,
        },
    }
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key,
    }

    client = get_async_client()
    response = await client.post(url, headers=headers, json=payload, timeout=90)
    if response.status_code >= 400:
        detail = response.text[:300]
        raise ValueError(f"ElevenLabs TTS: {detail or response.status_code}")
    audio = response.content

    if not audio:
        raise ValueError("ElevenLabs TTS returned empty audio")

    dest_dir = settings.media_storage_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.mp3"
    dest = dest_dir / filename
    dest.write_bytes(audio)
    public_url = f"{settings.public_base_url.rstrip('/')}/static/generated/{filename}"
    logger.info("ElevenLabs TTS ok voice=%s bytes=%s", voice_id, len(audio))
    return public_url
