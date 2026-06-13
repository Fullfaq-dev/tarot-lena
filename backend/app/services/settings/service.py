from sqlalchemy import select

from app.database.models import User, UserSettings
from app.database.session import AsyncSessionLocal
from app.bot.i18n import LANGUAGE_LABELS, normalize_language, t
from app.services.locale.service import LocaleService

VOICE_PRESETS = [
    ("female_mystical", "Мистический женский"),
    ("male_calm", "Спокойный мужской"),
    ("neutral_soft", "Мягкий нейтральный"),
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
        voice_label = dict(VOICE_PRESETS).get(settings.voice_preset, settings.voice_preset)
        tz_label = dict(TIMEZONE_OPTIONS).get(settings.timezone, settings.timezone)
        daily = "вкл" if settings.daily_card_enabled else "выкл"
        proactive = "вкл" if settings.proactive_messages_enabled else "выкл"
        language_label = LANGUAGE_LABELS.get(lang, lang)
        if lang == "en":
            return (
                "Settings\n\n"
                f"Language: {language_label}\n"
                f"Voice: {voice_label}\n"
                f"Timezone: {tz_label}\n"
                f"Quiet hours: {settings.quiet_hours_start} – {settings.quiet_hours_end}\n"
                f"Morning daily card: {'on' if settings.daily_card_enabled else 'off'}\n"
                f"Proactive messages: {'on' if settings.proactive_messages_enabled else 'off'}\n\n"
                "Tap a button below to change a setting or profile data."
            )
        if lang == "es":
            return (
                "Ajustes\n\n"
                f"Idioma: {language_label}\n"
                f"Voz: {voice_label}\n"
                f"Zona horaria: {tz_label}\n"
                f"Horas silenciosas: {settings.quiet_hours_start} – {settings.quiet_hours_end}\n"
                f"Carta del día por la mañana: {'sí' if settings.daily_card_enabled else 'no'}\n"
                f"Mensajes proactivos: {'sí' if settings.proactive_messages_enabled else 'no'}\n\n"
                "Toca un botón abajo para cambiar un ajuste o los datos del perfil."
            )
        if lang == "pt":
            return (
                "Configurações\n\n"
                f"Idioma: {language_label}\n"
                f"Voz: {voice_label}\n"
                f"Fuso horário: {tz_label}\n"
                f"Horário silencioso: {settings.quiet_hours_start} – {settings.quiet_hours_end}\n"
                f"Carta do dia de manhã: {'sim' if settings.daily_card_enabled else 'não'}\n"
                f"Mensagens proativas: {'sim' if settings.proactive_messages_enabled else 'não'}\n\n"
                "Toque um botão abaixo para alterar uma configuração ou os dados do perfil."
            )
        return (
            "Настройки\n\n"
            f"Язык: {language_label}\n"
            f"Голос ответов: {voice_label}\n"
            f"Часовой пояс: {tz_label}\n"
            f"Тихие часы: {settings.quiet_hours_start} – {settings.quiet_hours_end}\n"
            f"Карта дня утром: {daily}\n"
            f"Проактивные сообщения: {proactive}\n\n"
            "Нажми кнопку ниже, чтобы изменить параметр или данные анкеты."
        )
