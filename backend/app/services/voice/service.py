import logging
import re

from app.core.config import get_settings
from app.services.ai.kie_client import KieClient
from app.services.media.audio_convert import ensure_mp3
from app.services.media.kie_tasks import wait_for_media_task
from app.services.media.kie_upload import KieFileUpload, kie_friendly_filename
from app.services.media.service import MediaJobService
from app.services.media.stored_file import StoredFile

logger = logging.getLogger(__name__)

VOICE_PRESETS = {
    "female_soft": "5l5f8iK3YPeGga21rQIX",
    "female_mystical": "Z3R5wn05IrDiVCyEkUrK",
    "male_mentor": "nPczCjzI2devNBz1zQrb",
    "male_calm": "LruHrtVF6PSyGItzMNHS",
    "neutral_soft": "Z3R5wn05IrDiVCyEkUrK",
}

# Fallback STT models if the configured whisper model is unavailable on KIE.
_STT_MODEL_FALLBACKS = (
    "openai/whisper-1",
    "whisper-1",
    "gpt-4o-mini-transcribe",
    "openai/gpt-4o-mini-transcribe",
)


def plain_text_for_tts(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:5000]


def _normalize_transcript(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^(transcript|текст|расшифровка)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = text.strip("`\"' ")
    return text.strip()


class VoiceService:
    def __init__(self) -> None:
        self.kie = KieClient()
        self.jobs = MediaJobService()
        self.upload = KieFileUpload()

    async def _kie_audio_url(self, stored: StoredFile) -> str:
        audio_path = await ensure_mp3(stored.path)
        return await self.upload.ensure_kie_url(
            local_path=audio_path,
            source_url=None,
            upload_path="voice",
            file_name=kie_friendly_filename(audio_path, kind="audio"),
            kind="audio",
        )

    def _stt_models(self) -> list[str]:
        settings = get_settings()
        primary = settings.kie_stt_model.strip()
        models: list[str] = []
        if primary:
            models.append(primary)
        for model in _STT_MODEL_FALLBACKS:
            if model not in models:
                models.append(model)
        return models

    async def transcribe(self, stored: StoredFile, *, user_id: str | None = None) -> str:
        try:
            audio_url = await self._kie_audio_url(stored)
        except Exception as exc:
            raise ValueError(f"загрузка аудио: {exc}") from exc

        payload = {
            "audio_url": audio_url,
            "language": "ru",
            "language_code": "ru",
        }
        settings = get_settings()
        callback_url = f"{settings.public_base_url.rstrip('/')}/callbacks/kie"
        last_error: Exception | None = None

        for model in self._stt_models():
            try:
                response = await self.kie.create_media_task(model, payload, callback_url=callback_url)
            except Exception as exc:
                last_error = exc
                logger.warning("KIE STT createTask failed for %s: %s", model, exc)
                continue

            task_id = KieClient.task_id_from_response(response)
            if not task_id:
                last_error = ValueError("Не удалось создать задачу распознавания речи")
                continue

            await self.jobs.create_job(
                "voice_stt",
                {**payload, "provider_task_id": task_id, "engine": model},
                user_id=user_id,
            )
            try:
                _, text = await wait_for_media_task(task_id, timeout_sec=120)
            except Exception as exc:
                last_error = exc
                logger.warning("KIE STT polling failed for %s: %s", model, exc)
                continue

            normalized = _normalize_transcript(text or "")
            if len(normalized) >= 2:
                return normalized

            last_error = ValueError("Не удалось распознать голосовое сообщение")

        raise ValueError(f"распознавание: {last_error}") from last_error

    async def synthesize_audio_url(
        self,
        user_id: str,
        text: str,
        preset: str = "female_mystical",
    ) -> str:
        settings = get_settings()
        voice = VOICE_PRESETS.get(preset, VOICE_PRESETS["female_mystical"])
        spoken_text = plain_text_for_tts(text)
        if not spoken_text:
            raise ValueError("Пустой текст для озвучки")

        payload = {
            "text": spoken_text,
            "voice": voice,
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "speed": 1.0,
            "timestamps": False,
            "language_code": "ru",
        }
        response = await self.kie.create_media_task(
            "elevenlabs/text-to-speech-turbo-2-5",
            payload,
            callback_url=f"{settings.public_base_url.rstrip('/')}/callbacks/kie",
        )
        task_id = KieClient.task_id_from_response(response)
        if not task_id:
            raise ValueError("Не удалось создать задачу озвучки")

        await self.jobs.create_job(
            "voice_tts",
            {**payload, "provider_task_id": task_id},
            user_id=user_id,
        )
        urls, _ = await wait_for_media_task(task_id, timeout_sec=180)
        if not urls:
            raise ValueError("Генератор не вернул аудиофайл")
        return urls[0]
