from aiogram.types import User as TelegramUser
from sqlalchemy import select

from app.bot.leia_texts import (
    LEGAL_CONSENT,
    ONBOARDING_COMPLETE,
    ONBOARDING_PROMPTS,
    ONBOARDING_RESUME,
    WELCOME,
    legal_url,
)
from app.database.models import (
    OnboardingSession,
    SoulProfile,
    Subscription,
    SubscriptionTier,
    User,
    UserSettings,
)
from app.database.session import AsyncSessionLocal

ONBOARDING_STEPS: list[tuple[str, str]] = [
    ("legal_consent", "legal_consent"),
    ("name", "name"),
    ("birth_date", "birth_date"),
    ("birth_time", "birth_time"),
    ("birth_city", "birth_city"),
]

ONBOARDING_STEP_KEYS = [step for step, _ in ONBOARDING_STEPS]


class OnboardingService:
    async def _user_lang(self, session, user_id: str, telegram_user: TelegramUser | None) -> str:
        return "ru"

    def prompt_for_step(self, step_key: str, lang: str = "ru") -> str:
        if step_key == "legal_consent":
            return LEGAL_CONSENT.format(legal_url=legal_url())
        return ONBOARDING_PROMPTS.get(step_key, f"Шаг: {step_key}")

    async def is_onboarded(self, telegram_user: TelegramUser | None) -> bool:
        if telegram_user is None:
            return False
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            return bool(user and user.is_onboarded)

    async def get_current_step_key(self, telegram_user: TelegramUser | None) -> str | None:
        if telegram_user is None:
            return None
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None or user.is_onboarded:
                return None
            onboarding = await session.scalar(
                select(OnboardingSession).where(
                    OnboardingSession.user_id == user.id,
                    OnboardingSession.completed_at.is_(None),
                )
            )
            return onboarding.current_step if onboarding else ONBOARDING_STEP_KEYS[0]

    async def go_back(self, telegram_user: TelegramUser | None) -> tuple[str | None, str | None]:
        if telegram_user is None:
            return None, None

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None or user.is_onboarded:
                return None, user.id if user else None

            onboarding = await session.scalar(
                select(OnboardingSession).where(
                    OnboardingSession.user_id == user.id,
                    OnboardingSession.completed_at.is_(None),
                )
            )
            if onboarding is None:
                return self.prompt_for_step(ONBOARDING_STEP_KEYS[0]), user.id

            current_index = next(
                (index for index, step in enumerate(ONBOARDING_STEP_KEYS) if step == onboarding.current_step),
                0,
            )
            if current_index == 0:
                return self.prompt_for_step(ONBOARDING_STEP_KEYS[0]), user.id

            prev_step = ONBOARDING_STEP_KEYS[current_index - 1]
            answers = dict(onboarding.answers or {})
            answers.pop(ONBOARDING_STEP_KEYS[current_index], None)
            onboarding.answers = answers
            onboarding.current_step = prev_step
            await session.commit()
            return self.prompt_for_step(prev_step), user.id

    async def start_or_resume(
        self, telegram_user: TelegramUser | None
    ) -> tuple[str, str | None, bool]:
        if telegram_user is None:
            return "Не получилось определить профиль. Попробуй ещё раз.", None, False

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_user.id))
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                    language_code=telegram_user.language_code,
                )
                session.add(user)
                await session.flush()
                session.add(UserSettings(user_id=user.id, ui_language="ru"))
                session.add(Subscription(user_id=user.id, tier=SubscriptionTier.FREE.value))
                session.add(OnboardingSession(user_id=user.id, current_step="legal_consent"))
                session.add(SoulProfile(user_id=user.id, name=telegram_user.first_name))
                await session.commit()

                from app.services.locale.service import invalidate_language_cache

                invalidate_language_cache(telegram_user.id)

                return (
                    f"{WELCOME}\n\n{self.prompt_for_step('legal_consent')}",
                    user.id,
                    True,
                )

            if user.is_onboarded:
                from app.bot.leia_texts import WELCOME_BACK
                return WELCOME_BACK, user.id, False

            onboarding = await session.scalar(
                select(OnboardingSession).where(
                    OnboardingSession.user_id == user.id,
                    OnboardingSession.completed_at.is_(None),
                )
            )
            step = onboarding.current_step if onboarding else ONBOARDING_STEP_KEYS[0]
            if step == "legal_consent":
                text = f"{WELCOME}\n\n{self.prompt_for_step(step)}"
            else:
                text = f"{ONBOARDING_RESUME}\n{self.prompt_for_step(step)}"
            return text, user.id, False

    async def advance_from_consent(self, telegram_user: TelegramUser | None) -> tuple[str | None, str | None]:
        return await self._advance_step(telegram_user, "legal_consent", "accepted")

    async def skip_birth_time(self, telegram_user: TelegramUser | None) -> tuple[str | None, str | None, bool]:
        return await self.handle_answer(telegram_user, "—")

    async def handle_answer(
        self, telegram_user: TelegramUser | None, answer: str
    ) -> tuple[str | None, str | None, bool]:
        if telegram_user is None:
            return None, None, False

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None or user.is_onboarded:
                return None, user.id if user else None, False

            onboarding = await session.scalar(
                select(OnboardingSession).where(
                    OnboardingSession.user_id == user.id,
                    OnboardingSession.completed_at.is_(None),
                )
            )
            if onboarding is None:
                onboarding = OnboardingSession(user_id=user.id, current_step="legal_consent")
                session.add(onboarding)

            current_index = next(
                (index for index, step in enumerate(ONBOARDING_STEP_KEYS) if step == onboarding.current_step),
                0,
            )
            step_key = ONBOARDING_STEP_KEYS[current_index]

            if step_key == "legal_consent":
                return self.prompt_for_step("legal_consent"), user.id, False

            answers = dict(onboarding.answers or {})
            answers[step_key] = answer.strip()
            onboarding.answers = answers

            if current_index + 1 < len(ONBOARDING_STEP_KEYS):
                next_step = ONBOARDING_STEP_KEYS[current_index + 1]
                onboarding.current_step = next_step
                await session.commit()
                return self.prompt_for_step(next_step), user.id, False

            await self._complete_profile(session, user, answers)
            await session.commit()
            return ONBOARDING_COMPLETE, user.id, True

    async def _advance_step(
        self, telegram_user: TelegramUser | None, step_key: str, answer: str
    ) -> tuple[str | None, str | None]:
        if telegram_user is None:
            return None, None
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, None
            onboarding = await session.scalar(
                select(OnboardingSession).where(
                    OnboardingSession.user_id == user.id,
                    OnboardingSession.completed_at.is_(None),
                )
            )
            if onboarding is None or onboarding.current_step != step_key:
                return None, user.id
            answers = dict(onboarding.answers or {})
            answers[step_key] = answer
            onboarding.answers = answers
            idx = ONBOARDING_STEP_KEYS.index(step_key)
            next_step = ONBOARDING_STEP_KEYS[idx + 1]
            onboarding.current_step = next_step
            await session.commit()
            return self.prompt_for_step(next_step), user.id

    async def _complete_profile(
        self, session, user: User, answers: dict[str, str]
    ) -> None:
        profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
        if profile is None:
            profile = SoulProfile(user_id=user.id)
            session.add(profile)

        from app.services.profile.service import ProfileService

        profile_service = ProfileService()
        for field_key, raw in answers.items():
            if field_key in ("legal_consent",):
                continue
            if raw and raw != "—":
                profile_service._apply_field(profile, field_key, raw)
        profile.preferences = {"onboarding_answers": answers}
        user.is_onboarded = True

        onboarding = await session.scalar(
            select(OnboardingSession).where(
                OnboardingSession.user_id == user.id,
                OnboardingSession.completed_at.is_(None),
            )
        )
        if onboarding:
            from app.database.base import utcnow

            onboarding.completed_at = utcnow()
