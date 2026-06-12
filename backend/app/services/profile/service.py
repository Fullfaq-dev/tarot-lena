from datetime import date

from sqlalchemy import select

from app.database.models import OnboardingSession, SoulProfile, User
from app.database.session import AsyncSessionLocal
from app.services.onboarding.service import ONBOARDING_STEP_MAP, ONBOARDING_STEPS

PROFILE_FIELD_LABELS: dict[str, str] = {
    "name": "Имя",
    "birth_date": "Дата рождения",
    "birth_time": "Время рождения",
    "birth_city": "Город рождения",
    "gender": "Пол",
    "relationship_status": "Семейное положение",
    "has_children": "Дети",
    "profession": "Сфера / работа",
    "six_month_goal": "Цель на 6 месяцев",
    "main_concern": "Что беспокоит",
    "belief_system": "Во что веришь",
}


class ProfileService:
    def prompt_for_field(self, field_key: str) -> str:
        return ONBOARDING_STEP_MAP.get(field_key, "Напиши новое значение.")

    async def get_profile_summary(self, telegram_id: int) -> tuple[str | None, list[tuple[str, str, str]]]:
        """Возвращает (ошибка, [(key, label, value), ...])."""
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы создать твой профиль.", []
            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            if profile is None:
                return "Профиль ещё не собран.", []

            rows: list[tuple[str, str, str]] = []
            for field_key, _ in ONBOARDING_STEPS:
                label = PROFILE_FIELD_LABELS.get(field_key, field_key)
                rows.append((field_key, label, self._display_value(profile, field_key)))
            return None, rows

    async def update_field(self, telegram_id: int, field_key: str, raw_value: str) -> str | None:
        if field_key not in PROFILE_FIELD_LABELS:
            return "Неизвестное поле профиля."

        value = raw_value.strip()
        if not value:
            return "Напиши непустое значение."

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы создать твой профиль."

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

        label = PROFILE_FIELD_LABELS[field_key]
        return f"Обновила «{label}»: {stored_value}"

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

    def _parse_birth_date(self, raw: str) -> date | None:
        from datetime import datetime

        for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).date()
            except ValueError:
                continue
        return None
