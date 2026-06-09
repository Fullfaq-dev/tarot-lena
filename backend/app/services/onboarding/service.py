from aiogram.types import User as TelegramUser
from sqlalchemy import select

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
    ("name", "Как к тебе обращаться?"),
    ("birth_date", "Напиши дату рождения в формате ДД.ММ.ГГГГ."),
    ("birth_time", "Во сколько ты родился/родилась? Если не знаешь, напиши «не знаю»."),
    ("birth_city", "В каком городе ты родился/родилась?"),
    ("gender", "Укажи пол."),
    ("relationship_status", "Какое сейчас семейное положение?"),
    ("has_children", "Есть ли дети?"),
    ("profession", "Чем ты занимаешься или в какой сфере работаешь?"),
    ("six_month_goal", "Какая главная цель на ближайшие 6 месяцев?"),
    ("main_concern", "Что сейчас беспокоит больше всего: отношения, деньги, карьера, здоровье, саморазвитие или другое?"),
    ("belief_system", "Во что тебе ближе верить: таро, астрология, нумерология, энергия, тонкие материи или все сразу?"),
]

ONBOARDING_STEP_MAP = dict(ONBOARDING_STEPS)


class OnboardingService:
    async def is_onboarded(self, telegram_user: TelegramUser | None) -> bool:
        if telegram_user is None:
            return False
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            return bool(user and user.is_onboarded)

    def prompt_for_step(self, step_key: str) -> str:
        return ONBOARDING_STEP_MAP.get(step_key, ONBOARDING_STEPS[0][1])

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
            return onboarding.current_step if onboarding else ONBOARDING_STEPS[0][0]

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
                return ONBOARDING_STEPS[0][1], user.id

            current_index = next(
                (index for index, (step, _) in enumerate(ONBOARDING_STEPS) if step == onboarding.current_step),
                0,
            )
            if current_index == 0:
                return ONBOARDING_STEPS[0][1], user.id

            prev_step, prev_prompt = ONBOARDING_STEPS[current_index - 1]
            answers = dict(onboarding.answers or {})
            answers.pop(ONBOARDING_STEPS[current_index][0], None)
            answers.pop(prev_step, None)
            onboarding.answers = answers
            onboarding.current_step = prev_step
            await session.commit()
            return prev_prompt, user.id

    async def start_or_resume(
        self, telegram_user: TelegramUser | None
    ) -> tuple[str, str | None, bool]:
        if telegram_user is None:
            return "Не получилось определить Telegram-профиль. Попробуй еще раз.", None, False

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
                session.add(UserSettings(user_id=user.id))
                session.add(Subscription(user_id=user.id, tier=SubscriptionTier.FREE.value))
                session.add(OnboardingSession(user_id=user.id))
                session.add(SoulProfile(user_id=user.id, name=telegram_user.first_name))
                await session.commit()

                return (
                    "Добро пожаловать. Я буду твоим личным эзотерическим наставником: "
                    "помогу с раскладами, прогнозами и бережно запомню важные события твоей истории.\n\n"
                    f"Начнем с анкеты.\n{ONBOARDING_STEPS[0][1]}",
                    user.id,
                    True,
                )

            if user.is_onboarded:
                return (
                    "Рада снова видеть тебя. Можешь задать вопрос, выбрать расклад или посмотреть карту дня.",
                    user.id,
                    False,
                )

            result = await session.execute(
                select(OnboardingSession).where(
                    OnboardingSession.user_id == user.id,
                    OnboardingSession.completed_at.is_(None),
                )
            )
            onboarding = result.scalar_one_or_none()
            step = onboarding.current_step if onboarding else ONBOARDING_STEPS[0][0]
            prompt = dict(ONBOARDING_STEPS).get(step, ONBOARDING_STEPS[0][1])
            return f"Продолжим анкету.\n{prompt}", user.id, False

    async def handle_answer(
        self, telegram_user: TelegramUser | None, answer: str
    ) -> tuple[str | None, str | None, bool]:
        if telegram_user is None:
            return None, None, False

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_user.id))
            user = result.scalar_one_or_none()
            if user is None or user.is_onboarded:
                return None, user.id if user else None, False

            result = await session.execute(
                select(OnboardingSession).where(
                    OnboardingSession.user_id == user.id,
                    OnboardingSession.completed_at.is_(None),
                )
            )
            onboarding = result.scalar_one_or_none()
            if onboarding is None:
                onboarding = OnboardingSession(user_id=user.id)
                session.add(onboarding)

            current_index = next(
                (index for index, (step, _) in enumerate(ONBOARDING_STEPS) if step == onboarding.current_step),
                0,
            )
            step_key = ONBOARDING_STEPS[current_index][0]
            answers = dict(onboarding.answers or {})
            answers[step_key] = answer.strip()
            onboarding.answers = answers

            if current_index + 1 < len(ONBOARDING_STEPS):
                next_step, next_prompt = ONBOARDING_STEPS[current_index + 1]
                onboarding.current_step = next_step
                await session.commit()
                return next_prompt, user.id, False

            await self._complete_profile(session, user, answers)
            await session.commit()
            return (
                "Готово. Я собрала твой первый профиль.\n\n"
                "Теперь можешь задать вопрос, попросить расклад или открыть карту дня. "
                "Со временем я буду запоминать важные события, цели и людей, о которых ты рассказываешь.",
                user.id,
                True,
            )

    async def _complete_profile(self, session, user: User, answers: dict[str, str]) -> None:
        result = await session.execute(select(SoulProfile).where(SoulProfile.user_id == user.id))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = SoulProfile(user_id=user.id)
            session.add(profile)

        from app.services.profile.service import ProfileService

        profile_service = ProfileService()
        for field_key, raw in answers.items():
            if raw:
                profile_service._apply_field(profile, field_key, raw)
        profile.preferences = {"onboarding_answers": answers}
        profile.archetype = "Искатель"
        profile.personal_arcana = "будет рассчитан после уточнения даты рождения"
        user.is_onboarded = True

        result = await session.execute(
            select(OnboardingSession).where(
                OnboardingSession.user_id == user.id,
                OnboardingSession.completed_at.is_(None),
            )
        )
        onboarding = result.scalar_one_or_none()
        if onboarding:
            from app.database.base import utcnow

            onboarding.completed_at = utcnow()

