import logging
import re

from app.core.config import get_settings
from app.services.ai.kie_client import KieClient
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

_TRANSCRIBE_PROMPT = (
    "Распознай речь в этом аудиофайле. "
    "Верни только текст сказанного, без комментариев, кавычек и пояснений."
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
        return await self.upload.ensure_kie_url(
            local_path=stored.path,
            source_url=stored.public_url,
            upload_path="voice",
            file_name=kie_friendly_filename(stored.path, kind="audio"),
            kind="audio",
        )

    async def transcribe(self, stored: StoredFile, *, user_id: str | None = None) -> str:
        try:
            audio_url = await self._kie_audio_url(stored)
        except Exception as exc:
            raise ValueError(f"загрузка аудио: {exc}") from exc

        text = await self._transcribe_via_gemini(audio_url)
        if text:
            await self.jobs.create_job(
                "voice_stt",
                {"audio_url": audio_url, "engine": "gemini-3-flash"},
                user_id=user_id,
            )
            return text

        logger.warning("Gemini STT unavailable, falling back to elevenlabs/speech-to-text")
        return await self._transcribe_via_elevenlabs(audio_url, user_id=user_id)

    async def _transcribe_via_gemini(self, audio_url: str) -> str | None:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _TRANSCRIBE_PROMPT},
                    {"type": "image_url", "image_url": {"url": audio_url}},
                ],
            }
        ]
        try:
            answer = await self.kie.chat_completion(messages, reasoning_effort="low")
        except Exception as exc:
            logger.warning("Gemini voice transcription failed: %s", exc)
            return None

        text = _normalize_transcript(answer)
        if len(text) < 2:
            return None
        return text

    async def _transcribe_via_elevenlabs(self, audio_url: str, *, user_id: str | None) -> str:
        settings = get_settings()
        payload = {
            "audio_url": audio_url,
            "language_code": "",
            "tag_audio_events": True,
            "diarize": True,
        }
        try:
            response = await self.kie.create_media_task(
                "elevenlabs/speech-to-text",
                payload,
                callback_url=f"{settings.public_base_url.rstrip('/')}/callbacks/kie",
            )
        except Exception as exc:
            raise ValueError(f"распознавание: {exc}") from exc

        task_id = KieClient.task_id_from_response(response)
        if not task_id:
            raise ValueError("Не удалось создать задачу распознавания речи")

        await self.jobs.create_job(
            "voice_stt",
            {**payload, "provider_task_id": task_id, "engine": "elevenlabs/speech-to-text"},
            user_id=user_id,
        )
        _, text = await wait_for_media_task(task_id, timeout_sec=120)
        if not text:
            raise ValueError("Не удалось распознать голосовое сообщение")
        return _normalize_transcript(text)

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
