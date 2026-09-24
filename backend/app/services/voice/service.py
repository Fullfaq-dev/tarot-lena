import logging
import re

from app.services.ai.openai_media import synthesize_speech, transcribe_audio
from app.services.media.service import MediaJobService
from app.services.media.stored_file import StoredFile

logger = logging.getLogger(__name__)


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
        self.jobs = MediaJobService()

    async def transcribe(self, stored: StoredFile, *, user_id: str | None = None) -> str:
        try:
            raw = await transcribe_audio(stored.path, language="ru")
        except Exception as exc:
            raise ValueError(f"распознавание: {exc}") from exc

        normalized = _normalize_transcript(raw)
        if len(normalized) < 2:
            raise ValueError("Не удалось распознать голосовое сообщение")

        await self.jobs.create_job(
            "voice_stt",
            {"engine": "openai", "language": "ru"},
            user_id=user_id,
        )
        return normalized

    async def synthesize_audio_url(
        self,
        user_id: str,
        text: str,
        preset: str = "female_mystical",
    ) -> str:
        spoken_text = plain_text_for_tts(text)
        if not spoken_text:
            raise ValueError("Пустой текст для озвучки")

        url = await synthesize_speech(spoken_text, preset=preset)
        await self.jobs.create_job(
            "voice_tts",
            {"engine": "openai", "preset": preset},
            user_id=user_id,
        )
        return url
