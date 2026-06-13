from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy import select

from app.bot.i18n import normalize_language
from app.database.models import User, UserSettings
from app.database.session import AsyncSessionLocal


class LocaleService:
    async def sync_from_telegram(self, telegram_user: TelegramUser | None) -> str:
        if telegram_user is None:
            return "en"

        lang = normalize_language(telegram_user.language_code)

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return lang

            if user.language_code != telegram_user.language_code:
                user.language_code = telegram_user.language_code

            settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
            if settings is None:
                settings = UserSettings(user_id=user.id, ui_language=lang)
                session.add(settings)
            elif not settings.language_locked:
                settings.ui_language = lang

            await session.commit()
            return normalize_language(settings.ui_language)

    async def get_language(self, telegram_id: int) -> str:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "en"
            settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
            if settings is None:
                return normalize_language(user.language_code)
            return normalize_language(settings.ui_language)

    async def lock_language(self, telegram_id: int, language: str) -> str:
        lang = normalize_language(language)
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return lang
            settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
            if settings is None:
                settings = UserSettings(user_id=user.id, ui_language=lang, language_locked=True)
                session.add(settings)
            else:
                settings.ui_language = lang
                settings.language_locked = True
            await session.commit()
            return lang
