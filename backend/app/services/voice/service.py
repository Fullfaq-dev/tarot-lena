import logging
import re

from app.core.config import get_settings
from app.services.ai.kie_client import KieClient
from app.services.media.kie_tasks import wait_for_media_task
from app.services.media.service import MediaJobService
from app.services.media.stored_file import StoredFile
from app.services.voice.stt_302 import Stt302Client

logger = logging.getLogger(__name__)

VOICE_PRESETS = {
    "female_soft": "5l5f8iK3YPeGga21rQIX",
    "female_mystical": "hLjwV7lYzk15SWLUmhEH",
    "male_mentor": "nPczCjzI2devNBz1zQrb",
    "male_calm": "LruHrtVF6PSyGItzMNHS",
    "neutral_soft": "hLjwV7lYzk15SWLUmhEH",
}


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
        self.stt = Stt302Client()
        self.jobs = MediaJobService()

    async def transcribe(self, stored: StoredFile, *, user_id: str | None = None) -> str:
        settings = get_settings()
        try:
            raw = await self.stt.transcribe_file(stored.path, language="ru")
        except Exception as exc:
            raise ValueError(f"распознавание: {exc}") from exc

        normalized = _normalize_transcript(raw)
        if len(normalized) < 2:
            raise ValueError("Не удалось распознать голосовое сообщение")

        await self.jobs.create_job(
            "voice_stt",
            {"engine": f"302.ai/{settings.ai302_stt_model}", "language": "ru"},
            user_id=user_id,
        )
        return normalized

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
