"""Official OpenAI media: STT, TTS, image edit. No KIE / 302 / ElevenLabs."""

from __future__ import annotations

import base64
import logging
import mimetypes
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.http import get_async_client
from app.services.media.audio_convert import ensure_mp3

logger = logging.getLogger(__name__)

_TTS_VOICES = {
    "female_soft": "shimmer",
    "female_mystical": "nova",
    "male_mentor": "onyx",
    "male_calm": "echo",
    "neutral_soft": "alloy",
}


def openai_key() -> str:
    key = (get_settings().openai_api_key or "").strip().strip('"').strip("'")
    if not key or key == "replace-me":
        raise ValueError("OPENAI_API_KEY не настроен")
    return key


def openai_headers(*, json_body: bool = True) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {openai_key()}"}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def file_to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def tts_voice_for_preset(preset: str) -> str:
    return _TTS_VOICES.get(preset) or (get_settings().openai_tts_voice or "nova")


def _save_bytes(data: bytes, *, suffix: str) -> str:
    settings = get_settings()
    dest_dir = settings.media_storage_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    dest = dest_dir / filename
    dest.write_bytes(data)
    return f"{settings.public_base_url.rstrip('/')}/static/generated/{filename}"


async def transcribe_audio(audio_path: Path, *, language: str = "ru") -> str:
    settings = get_settings()
    path = await ensure_mp3(audio_path)
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError("Пустой аудиофайл")

    mime = "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/ogg"
    file_bytes = path.read_bytes()
    models = [settings.openai_stt_model.strip() or "gpt-transcribe"]
    for extra in ("gpt-transcribe", "whisper-1"):
        if extra not in models:
            models.append(extra)

    client = get_async_client()
    last_error: Exception | None = None
    url = f"{settings.openai_base_url.rstrip('/')}/audio/transcriptions"
    for model in models:
        form: dict[str, str] = {"model": model}
        if model == "whisper-1":
            form["language"] = language
        else:
            form["language"] = language
        try:
            response = await client.post(
                url,
                headers=openai_headers(json_body=False),
                data=form,
                files={"file": (path.name, file_bytes, mime)},
                timeout=120,
            )
        except Exception as exc:
            last_error = exc
            logger.warning("OpenAI STT transport model=%s: %s", model, exc)
            continue
        if response.status_code >= 400:
            detail = response.text.strip()[:400]
            last_error = ValueError(f"OpenAI STT: {detail or response.status_code}")
            logger.warning("OpenAI STT failed model=%s status=%s body=%s", model, response.status_code, detail)
            continue
        body = response.json()
        text = body.get("text") if isinstance(body, dict) else None
        if isinstance(text, str) and text.strip():
            logger.info("OpenAI STT ok model=%s chars=%s", model, len(text.strip()))
            return text.strip()
        last_error = ValueError("OpenAI не вернул текст расшифровки")
    raise last_error or ValueError("OpenAI STT failed")


async def synthesize_speech(text: str, *, preset: str = "female_mystical") -> str:
    settings = get_settings()
    spoken = (text or "").strip()
    if not spoken:
        raise ValueError("Пустой текст для озвучки")
    payload = {
        "model": settings.openai_tts_model or "gpt-4o-mini-tts",
        "voice": tts_voice_for_preset(preset),
        "input": spoken[:4096],
        "response_format": "mp3",
        "instructions": "Говори спокойно, мягко, по-русски, как внимательный эзотерический гид.",
    }
    client = get_async_client()
    url = f"{settings.openai_base_url.rstrip('/')}/audio/speech"
    response = await client.post(url, headers=openai_headers(), json=payload, timeout=90)
    if response.status_code >= 400 and "instructions" in payload:
        payload.pop("instructions", None)
        response = await client.post(url, headers=openai_headers(), json=payload, timeout=90)
    if response.status_code >= 400:
        detail = response.text.strip()[:400]
        raise ValueError(f"OpenAI TTS: {detail or response.status_code}")
    audio = response.content
    if not audio:
        raise ValueError("OpenAI TTS вернул пустое аудио")
    url = _save_bytes(audio, suffix=".mp3")
    logger.info("OpenAI TTS ok voice=%s bytes=%s", payload["voice"], len(audio))
    return url


async def edit_image(
    source_path: Path,
    *,
    prompt: str,
    size: str = "1024x1536",
) -> list[str]:
    settings = get_settings()
    if not source_path.exists() or source_path.stat().st_size == 0:
        raise ValueError("Нет исходного фото для генерации")
    mime = mimetypes.guess_type(source_path.name)[0] or "image/jpeg"
    model = settings.openai_image_model or "gpt-image-2"
    client = get_async_client()
    response = await client.post(
        f"{settings.openai_base_url.rstrip('/')}/images/edits",
        headers=openai_headers(json_body=False),
        data={
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": "medium",
        },
        files={"image": (source_path.name, source_path.read_bytes(), mime)},
        timeout=180,
    )
    if response.status_code >= 400:
        detail = response.text.strip()[:500]
        raise ValueError(f"OpenAI image: {detail or response.status_code}")
    body = response.json()
    urls: list[str] = []
    for item in body.get("data") or []:
        if not isinstance(item, dict):
            continue
        if item.get("url"):
            urls.append(str(item["url"]))
            continue
        raw = item.get("b64_json")
        if isinstance(raw, str) and raw.strip():
            urls.append(_save_bytes(base64.b64decode(raw), suffix=".png"))
    if not urls:
        raise ValueError("OpenAI не вернул картинку")
    logger.info("OpenAI image edit ok model=%s urls=%s", model, len(urls))
    return urls
