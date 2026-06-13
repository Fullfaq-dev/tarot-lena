from sqlalchemy import select

from app.database.models import User, UserSettings
from app.database.session import AsyncSessionLocal
from app.bot.i18n import LANGUAGE_LABELS, normalize_language, t
from app.bot.i18n_services import VOICE_PRESET_I18N
from app.services.locale.service import LocaleService

VOICE_PRESETS = [
    ("female_mystical", "voice_preset_female"),
    ("male_calm", "voice_preset_male"),
    ("neutral_soft", "voice_preset_neutral"),
]

TIMEZONE_OPTIONS = [
    ("Europe/Moscow", "Москва"),
    ("Europe/Kaliningrad", "Калининград"),
    ("Asia/Yekaterinburg", "Екатеринбург"),
    ("Asia/Novosibirsk", "Новосибирск"),
    ("Asia/Vladivostok", "Владивосток"),
]


class SettingsService:
    async def get_panel_text(self, telegram_id: int) -> str:
        settings = await self._load_settings(telegram_id)
        if settings is None:
            lang = await LocaleService().get_language(telegram_id)
            return t("error_need_start", lang)
        return self._format_panel(settings)

    async def get_ui_language(self, telegram_id: int) -> str:
        return await LocaleService().get_language(telegram_id)

    async def set_ui_language(self, telegram_id: int, language: str) -> str:
        lang = await LocaleService().lock_language(telegram_id, language)
        panel = await self.get_panel_text(telegram_id)
        label = LANGUAGE_LABELS.get(lang, lang)
        return f"{t('language_changed', lang).format(label=label)}\n\n{panel}"

    async def toggle_daily_card(self, telegram_id: int) -> str:
        return await self._mutate(telegram_id, lambda settings: setattr(
            settings, "daily_card_enabled", not settings.daily_card_enabled
        ))

    async def toggle_proactive(self, telegram_id: int) -> str:
        return await self._mutate(telegram_id, lambda settings: setattr(
            settings, "proactive_messages_enabled", not settings.proactive_messages_enabled
        ))

    async def cycle_voice(self, telegram_id: int) -> str:
        def mutate(settings: UserSettings) -> None:
            presets = [preset for preset, _ in VOICE_PRESETS]
            try:
                index = presets.index(settings.voice_preset)
            except ValueError:
                index = 0
            settings.voice_preset = presets[(index + 1) % len(presets)]

        return await self._mutate(telegram_id, mutate)

    async def cycle_timezone(self, telegram_id: int) -> str:
        def mutate(settings: UserSettings) -> None:
            zones = [zone for zone, _ in TIMEZONE_OPTIONS]
            try:
                index = zones.index(settings.timezone)
            except ValueError:
                index = 0
            settings.timezone = zones[(index + 1) % len(zones)]

        return await self._mutate(telegram_id, mutate)

    async def _mutate(self, telegram_id: int, mutate) -> str:
        async with AsyncSessionLocal() as session:
            settings = await self._load_settings_in_session(session, telegram_id)
            if settings is None:
                lang = await LocaleService().get_language(telegram_id)
                return t("error_need_start", lang)
            mutate(settings)
            await session.commit()
            await session.refresh(settings)
            return self._format_panel(settings)

    async def _load_settings(self, telegram_id: int) -> UserSettings | None:
        async with AsyncSessionLocal() as session:
            return await self._load_settings_in_session(session, telegram_id)

    async def _load_settings_in_session(self, session, telegram_id: int) -> UserSettings | None:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return None
        settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
        if settings is None:
            settings = UserSettings(user_id=user.id)
            session.add(settings)
            await session.flush()
        return settings

    def _format_panel(self, settings: UserSettings) -> str:
        lang = normalize_language(settings.ui_language)
        voice_label = t(
            VOICE_PRESET_I18N.get(settings.voice_preset, "voice_preset_female"),
            lang,
        )
        tz_label = dict(TIMEZONE_OPTIONS).get(settings.timezone, settings.timezone)
        language_label = LANGUAGE_LABELS.get(lang, lang)
        daily = (
            t("settings_toggle_on", lang)
            if settings.daily_card_enabled
            else t("settings_toggle_off", lang)
        )
        proactive = (
            t("settings_toggle_on", lang)
            if settings.proactive_messages_enabled
            else t("settings_toggle_off", lang)
        )
        return t(
            "settings_panel",
            lang,
            language=language_label,
            voice=voice_label,
            timezone=tz_label,
            quiet_start=settings.quiet_hours_start,
            quiet_end=settings.quiet_hours_end,
            daily=daily,
            proactive=proactive,
        )
