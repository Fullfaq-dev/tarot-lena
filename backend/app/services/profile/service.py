from datetime import date

from sqlalchemy import select

from app.bot.i18n import normalize_language, onboarding_step_prompt, t
from app.bot.i18n_services import PROFILE_FIELD_I18N
from app.database.models import OnboardingSession, SoulProfile, User, UserSettings
from app.database.session import AsyncSessionLocal
from app.services.onboarding.service import ONBOARDING_STEPS


class ProfileService:
    async def _lang(self, telegram_id: int) -> str:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "en"
            settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
            return normalize_language(settings.ui_language if settings else "en")

    def field_label(self, field_key: str, lang: str) -> str:
        key = PROFILE_FIELD_I18N.get(field_key)
        return t(key, lang) if key else field_key

    def prompt_for_field(self, field_key: str, lang: str = "ru") -> str:
        lang = normalize_language(lang)
        if field_key in {k for k, _ in ONBOARDING_STEPS}:
            return onboarding_step_prompt(field_key, lang)
        return t("profile_prompt_default", lang)

    async def get_profile_summary(self, telegram_id: int) -> tuple[str | None, list[tuple[str, str, str]]]:
        lang = await self._lang(telegram_id)
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", lang), []
            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            if profile is None:
                return t("profile_not_collected_short", lang), []

            rows: list[tuple[str, str, str]] = []
            for field_key, _ in ONBOARDING_STEPS:
                label = self.field_label(field_key, lang)
                rows.append((field_key, label, self._display_value(profile, field_key)))
            return None, rows

    async def update_field(self, telegram_id: int, field_key: str, raw_value: str) -> str | None:
        lang = await self._lang(telegram_id)
        if field_key not in PROFILE_FIELD_I18N:
            return t("profile_field_unknown", lang)

        value = raw_value.strip()
        if not value:
            return t("profile_empty_value", lang)

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", lang)

            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            if profile is None:
                profile = SoulProfile(user_id=user.id)
                session.add(profile)

            stored_value = self._apply_field(profile, field_key, value)
            prefs = dict(profile.preferences or {})
            answers = dict(prefs.get("onboarding_answers") or {})
            answers[field_key] = stored_value
            prefs["onboarding_answers"] = answers
            profile.preferences = prefs

            onboarding = await session.scalar(
                select(OnboardingSession).where(OnboardingSession.user_id == user.id)
            )
            if onboarding is not None:
                onb_answers = dict(onboarding.answers or {})
                onb_answers[field_key] = stored_value
                onboarding.answers = onb_answers

            await session.commit()

        label = self.field_label(field_key, lang)
        return t("profile_updated", lang, label=label, value=stored_value)

    def _display_value(self, profile: SoulProfile, field_key: str) -> str:
        if field_key == "birth_date" and profile.birth_date:
            return profile.birth_date.strftime("%d.%m.%Y")
        value = getattr(profile, field_key, None)
        if value:
            text = str(value)
            return text if len(text) <= 28 else text[:27] + "…"
        answers = (profile.preferences or {}).get("onboarding_answers") or {}
        fallback = answers.get(field_key)
        if fallback:
            text = str(fallback)
            return text if len(text) <= 28 else text[:27] + "…"
        return "—"

    def _apply_field(self, profile: SoulProfile, field_key: str, value: str) -> str:
        if field_key == "birth_date":
            parsed = self._parse_birth_date(value)
            profile.birth_date = parsed
            return value if parsed is None else parsed.strftime("%d.%m.%Y")
        setattr(profile, field_key, value)
        return value

    def _parse_birth_date(self, value: str) -> date | None:
        from datetime import datetime

        for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        return None
