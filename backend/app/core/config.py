from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "Лея — Таро и Нумерология"
    public_base_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://tarot:tarot@localhost:5432/tarot"
    redis_url: str = "redis://localhost:6379/0"

    telegram_bot_token: str = "replace-me"
    telegram_webhook_secret: str = "replace-me"
    telegram_use_polling: bool = False
    telegram_admin_ids: str = "267409502,7670490295"
    telegram_placeholder_sticker_id: str = ""

    # Personal owner who receives new-user and top-up notifications.
    owner_telegram_id: int = 7670490295
    # Channel users must join to claim the one-time gift (username without @).
    gift_channel_username: str = "arcana_tarot_ai"

    kie_api_key: str = "replace-me"
    kie_base_url: str = "https://api.kie.ai"
    kie_file_upload_base_url: str = "https://kieai.redpandaai.co"
    kie_callback_secret: str = "replace-me"
    kie_credit_usd: float = 0.005
    kie_input_credits_per_1m: float = 87.5
    kie_output_credits_per_1m: float = 700
    kie_chat_model: str = "gpt-5-2"

    ai302_api_key: str = "replace-me"
    ai302_base_url: str = "https://api.302.ai"
    ai302_stt_model: str = "whisper-1"

    elevenlabs_api_key: str = "replace-me"
    elevenlabs_tts_model: str = "eleven_turbo_v2_5"
    elevenlabs_default_voice_id: str = "hLjwV7lYzk15SWLUmhEH"

    billing_credit_usd: float = 0.007
    charge_markup: float = 50
    provider_cost_display_multiplier: float = 2
    image_generation_provider_cost_usd: float = 0.05
    image_generation_markup: float = 5

    jwt_secret: str = "replace-me"
    admin_bootstrap_email: str = "admin@arcaneai.online"
    admin_bootstrap_password: str = "ArcanaPanel#2026!Km"
    legal_page_url: str = "https://arcaneai.online/"
    support_telegram_url: str = "https://t.me/OnePage_support"

    platega_merchant_id: str = Field(default="", alias="PLATEGA_MERCHANT_ID")
    platega_api_key: str = Field(default="", alias="PLATEGA_API_KEY")
    platega_webhook_secret: str = Field(default="", alias="PLATEGA_WEBHOOK_SECRET")
    platega_payment_method: int = Field(default=0, alias="PLATEGA_PAYMENT_METHOD")
    platega_return_url: str = Field(default="", alias="PLATEGA_RETURN_URL")
    platega_failed_url: str = Field(default="", alias="PLATEGA_FAILED_URL")
    payments_demo_mode: bool = Field(default=True, alias="PAYMENTS_DEMO_MODE")

    @property
    def platega_configured(self) -> bool:
        return bool(self.platega_merchant_id and self.platega_api_key)

    @property
    def platega_callback_url(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/callbacks/platega"

    media_storage_dir: Path = Path("backend/static/generated")
    tarot_cards_dir: Path = Path("Cards-jpg")

    @property
    def webhook_url(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/telegram/webhook"

    @property
    def gift_channel_chat_id(self) -> str:
        return f"@{self.gift_channel_username.lstrip('@')}"

    @property
    def gift_channel_url(self) -> str:
        return f"https://t.me/{self.gift_channel_username.lstrip('@')}"

    @property
    def admin_ids(self) -> set[int]:
        return {int(value) for value in self.telegram_admin_ids.split(",") if value.strip().isdigit()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
