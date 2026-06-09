from app.core.config import get_settings
from app.services.ai.kie_client import KieClient
from app.services.media.service import MediaJobService

VOICE_PRESETS = {
    "female_soft": "5l5f8iK3YPeGga21rQIX",
    "female_mystical": "Z3R5wn05IrDiVCyEkUrK",
    "male_mentor": "nPczCjzI2devNBz1zQrb",
    "male_calm": "LruHrtVF6PSyGItzMNHS",
}


class VoiceService:
    def __init__(self) -> None:
        self.kie = KieClient()
        self.jobs = MediaJobService()

    async def transcribe(self, file_url: str) -> str:
        return f"Текст из голосового будет распознан через Whisper adapter. Файл: {file_url}"

    async def synthesize(self, user_id: str, text: str, preset: str = "female_mystical"):
        settings = get_settings()
        voice = VOICE_PRESETS.get(preset, VOICE_PRESETS["female_mystical"])
        payload = {
            "text": text[:5000],
            "voice": voice,
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.15,
            "speed": 0.95,
            "timestamps": False,
            "language_code": "ru",
        }
        response = await self.kie.create_media_task(
            "elevenlabs/text-to-speech-turbo-2-5",
            payload,
            callback_url=f"{settings.public_base_url.rstrip('/')}/callbacks/kie",
        )
        return await self.jobs.create_job(
            "voice_tts",
            {**payload, "provider_task_id": response.get("data", {}).get("taskId")},
            user_id=user_id,
        )
