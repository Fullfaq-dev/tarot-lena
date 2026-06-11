from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "AI Tarot Bot"
    public_base_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://tarot:tarot@localhost:5432/tarot"
    redis_url: str = "redis://localhost:6379/0"

    telegram_bot_token: str = "replace-me"
    telegram_webhook_secret: str = "replace-me"
    telegram_admin_ids: str = ""
    telegram_placeholder_sticker_id: str = ""

    kie_api_key: str = "replace-me"
    kie_base_url: str = "https://api.kie.ai"
    kie_file_upload_base_url: str = "https://kieai.redpandaai.co"
    kie_callback_secret: str = "replace-me"
    kie_credit_usd: float = 0.005
    kie_input_credits_per_1m: float = 87.5
    kie_output_credits_per_1m: float = 700
    kie_chat_model: str = "gpt-5-2"
    kie_stt_model: str = "elevenlabs/speech-to-text"
    billing_credit_usd: float = 0.007
    charge_markup: float = 50
    provider_cost_display_multiplier: float = 2
    image_generation_provider_cost_usd: float = 0.05
    image_generation_markup: float = 5

    jwt_secret: str = "replace-me"
    admin_bootstrap_email: str = "admin@example.com"
    admin_bootstrap_password: str = "change-me"

    platega_merchant_id: str = Field(default="", alias="PLATEGA_MERCHANT_ID")
    platega_api_key: str = ""
    platega_webhook_secret: str = ""

    media_storage_dir: Path = Path("backend/static/generated")
    tarot_cards_dir: Path = Path("Cards-jpg")

    @property
    def webhook_url(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/telegram/webhook"

    @property
    def admin_ids(self) -> set[int]:
        return {int(value) for value in self.telegram_admin_ids.split(",") if value.strip().isdigit()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
