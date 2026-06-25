from __future__ import annotations

import time

from aiogram.types import User as TelegramUser
from sqlalchemy import select

from app.bot.i18n import normalize_language
from app.database.models import User, UserSettings
from app.database.session import AsyncSessionLocal

# In-process TTL cache for resolved UI language keyed by telegram_id.
# The bot runs as a single webhook worker, so a module-level cache safely
# collapses the burst of identical language lookups that happen on every
# update (middleware + handler + service) into a single DB read.
_LANG_CACHE: dict[int, tuple[str, float]] = {}
_LANG_TTL = 300.0


def _cache_get(telegram_id: int) -> str | None:
    entry = _LANG_CACHE.get(telegram_id)
    if entry is None:
        return None
    lang, expires_at = entry
    if expires_at < time.monotonic():
        _LANG_CACHE.pop(telegram_id, None)
        return None
    return lang


def _cache_set(telegram_id: int, lang: str) -> None:
    _LANG_CACHE[telegram_id] = (lang, time.monotonic() + _LANG_TTL)


def invalidate_language_cache(telegram_id: int) -> None:
    _LANG_CACHE.pop(telegram_id, None)


class LocaleService:
    async def sync_from_telegram(self, telegram_user: TelegramUser | None) -> str:
        if telegram_user is None:
            return "en"

        cached = _cache_get(telegram_user.id)
        if cached is not None:
            return cached

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
            resolved = normalize_language(settings.ui_language)
            _cache_set(telegram_user.id, resolved)
            return resolved

    async def get_language(self, telegram_id: int) -> str:
        cached = _cache_get(telegram_id)
        if cached is not None:
            return cached

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "en"
            settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
            resolved = (
                normalize_language(user.language_code)
                if settings is None
                else normalize_language(settings.ui_language)
            )
            _cache_set(telegram_id, resolved)
            return resolved

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
            _cache_set(telegram_id, lang)
            return lang
