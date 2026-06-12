import random
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import func, select

from app.database.models import DailyPrediction, TarotCard, TarotReading, User
from app.database.session import AsyncSessionLocal
from app.core.config import get_settings
from app.services.billing.limits import DAILY_READINGS_LIMIT, HISTORY_PAGE_SIZE
from app.services.ai.context import ContextBuilder
from app.services.ai.kie_client import KieClient
from app.services.tarot.cards import FULL_DECK, storage_image_path
from app.services.tarot.daily_card import pick_daily_card_with_ai

READING_TYPES = {
    "day": 1,
    "week": 3,
    "month": 5,
    "love": 3,
    "relationship": 5,
    "money": 3,
    "career": 3,
    "choice": 2,
    "past_present_future": 3,
    "compatibility": 6,
}


READING_TYPE_LABELS = {
    "love": "Любовь",
    "relationship": "Отношения",
    "money": "Деньги",
    "career": "Карьера",
    "choice": "Выбор решения",
    "past_present_future": "Прошлое / настоящее / будущее",
    "compatibility": "Совместимость",
}


class TarotService:
    def __init__(self) -> None:
        self.kie = KieClient()
        self.context_builder = ContextBuilder()

    async def menu_text(self, selected: str) -> str:
        if selected == "История раскладов":
            return "История раскладов уже сохраняется. Скоро здесь будет список прошлых вопросов, карт и толкований."
        return (
            "Доступные расклады: карта дня, любовь, отношения, деньги, карьера, выбор решения, "
            "прошлое / настоящее / будущее, совместимость.\n\n"
            "Напиши вопрос обычным сообщением, а я сделаю расклад и объясню карты простым языком."
        )

    async def daily_card_for_telegram(self, telegram_id: int) -> tuple[str, dict | None]:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы создать твой профиль.", None

            existing = await session.scalar(
                select(DailyPrediction).where(
                    DailyPrediction.user_id == user.id,
                    DailyPrediction.prediction_date == date.today(),
                )
            )
            if existing:
                card = await self._card_dict_from_prediction(session, existing)
                if card is None:
                    card = self._resolve_card_from_text(existing.text)
                if card is not None and not self._is_stale_daily_text(existing.text):
                    return existing.text, card
                await session.delete(existing)
                await session.flush()

            messages = await self.context_builder.build(
                session, user, user_query="карта дня на сегодня"
            )
            try:
                picked, interpretation = await pick_daily_card_with_ai(messages, self.kie)
            except ValueError:
                picked = self.draw_cards(1)[0]
                interpretation = (
                    f"Сегодня с тобой **{picked['name']}**.\n\n"
                    f"В эзотерической интерпретации это может означать: {picked['description']}.\n"
                    "Прислушайся к знакам дня и не торопи то, что должно раскрыться естественно."
                )

            card = self._attach_image_path(picked)
            text = interpretation.strip()
            if card["name"] not in text:
                text = f"**Карта дня — {card['name']}**\n\n{text}"

            db_card = await session.scalar(select(TarotCard).where(TarotCard.slug == str(card["slug"])))
            session.add(
                DailyPrediction(
                    user_id=user.id,
                    prediction_date=date.today(),
                    tarot_card_id=db_card.id if db_card else None,
                    text=text,
                )
            )
            await session.commit()
            return text, card

    async def _card_dict_from_prediction(
        self, session, prediction: DailyPrediction
    ) -> dict | None:
        if not prediction.tarot_card_id:
            return None
        db_card = await session.get(TarotCard, prediction.tarot_card_id)
        if db_card is None:
            return None
        return self._attach_image_path(
            {
                "slug": db_card.slug,
                "name": db_card.name,
                "description": db_card.description,
                "image_file": Path(db_card.image_path).name,
            }
        )

    def _attach_image_path(self, card: dict) -> dict:
        settings = get_settings()
        return {
            **card,
            "image_path": storage_image_path(card, settings.tarot_cards_dir),
        }

    def _resolve_card_from_text(self, text: str) -> dict | None:
        normalized = text.strip()
        if not normalized:
            return None
        for deck_card in FULL_DECK:
            name = str(deck_card["name"])
            if name in normalized:
                return self._attach_image_path(dict(deck_card))
        return None

    @staticmethod
    def _is_stale_daily_text(text: str) -> bool:
        return "В эзотерической интерпретации это может означать" in text

    def _today_start_utc() -> datetime:
        now = datetime.now(UTC)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    async def ensure_can_read_today(self, telegram_id: int) -> tuple[bool, str | None]:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return False, "Сначала нажми /start, чтобы создать твой профиль."
            count = await session.scalar(
                select(func.count())
                .select_from(TarotReading)
                .where(
                    TarotReading.user_id == user.id,
                    TarotReading.created_at >= self._today_start_utc(),
                )
            )
            used = int(count or 0)
            if used >= DAILY_READINGS_LIMIT:
                return (
                    False,
                    f"Сегодня уже {DAILY_READINGS_LIMIT} раскладов — дневной лимит исчерпан. "
                    "Новые расклады будут доступны завтра.",
                )
            return True, None

    async def readings_left_today(self, telegram_id: int) -> int:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return 0
            count = await session.scalar(
                select(func.count())
                .select_from(TarotReading)
                .where(
                    TarotReading.user_id == user.id,
                    TarotReading.created_at >= self._today_start_utc(),
                )
            )
            return max(0, DAILY_READINGS_LIMIT - int(count or 0))

    async def create_reading(
        self,
        user_id: str,
        reading_type: str,
        question: str,
        *,
        cards: list[dict] | None = None,
        interpretation: str | None = None,
    ) -> TarotReading:
        count = READING_TYPES.get(reading_type, 3)
        drawn_cards = cards or self.draw_cards(count)
        text = interpretation or self.interpret_locally(question, drawn_cards)
        async with AsyncSessionLocal() as session:
            reading = TarotReading(
                user_id=user_id,
                reading_type=reading_type,
                question=question,
                cards=drawn_cards,
                interpretation=text,
            )
            session.add(reading)
            await session.commit()
            await session.refresh(reading)
            return reading

    def draw_cards(self, count: int) -> list[dict]:
        settings = get_settings()
        cards = random.sample(FULL_DECK, k=min(count, len(FULL_DECK)))
        return [
            {
                **card,
                "image_path": storage_image_path(card, settings.tarot_cards_dir),
            }
            for card in cards
        ]

    async def history_page(
        self, telegram_id: int, page: int = 0
    ) -> tuple[str, list[TarotReading], int, int]:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы создать твой профиль.", [], 0, 0

            total = await session.scalar(
                select(func.count())
                .select_from(TarotReading)
                .where(TarotReading.user_id == user.id)
            )
            total = int(total or 0)
            if total == 0:
                return (
                    "Пока раскладов нет. Выбери «Сделать расклад» или просто задай вопрос в чате.",
                    [],
                    0,
                    0,
                )

            total_pages = max(1, (total + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)
            page = max(0, min(page, total_pages - 1))
            offset = page * HISTORY_PAGE_SIZE

            readings = await session.scalars(
                select(TarotReading)
                .where(TarotReading.user_id == user.id)
                .order_by(TarotReading.created_at.desc())
                .offset(offset)
                .limit(HISTORY_PAGE_SIZE)
            )
            items = list(readings)

            lines = [
                "История раскладов",
                f"Страница {page + 1} из {total_pages}\n",
                "Нажми на расклад, чтобы открыть полное толкование:\n",
            ]
            for index, reading in enumerate(items, start=offset + 1):
                label = READING_TYPE_LABELS.get(reading.reading_type, reading.reading_type)
                question = reading.question[:60] + ("…" if len(reading.question) > 60 else "")
                lines.append(f"{index}. {label} — «{question}»")
            return "\n".join(lines), items, page, total_pages

    async def history_entries(self, telegram_id: int) -> tuple[str, list[TarotReading]]:
        text, items, _, _ = await self.history_page(telegram_id, page=0)
        return text, items

    async def history_for_telegram(self, telegram_id: int) -> str:
        text, _ = await self.history_entries(telegram_id)
        return text

    async def reading_detail_for_telegram(self, telegram_id: int, reading_id: str) -> str | None:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return None
            reading = await session.scalar(
                select(TarotReading).where(
                    TarotReading.id == reading_id,
                    TarotReading.user_id == user.id,
                )
            )
            if reading is None:
                return None
            return self.format_reading_message(
                reading.reading_type,
                reading.question,
                reading.cards,
                reading.interpretation,
            )

    async def profile_for_telegram(self, telegram_id: int) -> str:
        from app.database.models import SoulProfile

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы создать твой профиль."

            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            if profile is None:
                return "Профиль ещё не собран. Нажми /start и пройди короткую анкету."

            birth_date = profile.birth_date.strftime("%d.%m.%Y") if profile.birth_date else "не указана"
            return (
                f"Имя: {profile.name or '—'}\n"
                f"Дата рождения: {birth_date}\n"
                f"Время рождения: {profile.birth_time or '—'}\n"
                f"Город рождения: {profile.birth_city or '—'}\n"
                f"Цель на 6 месяцев: {profile.six_month_goal or '—'}\n"
                f"Сейчас беспокоит: {profile.main_concern or '—'}\n"
                f"Ближе всего: {profile.belief_system or '—'}"
            )

    async def profile_extended_for_telegram(self, telegram_id: int) -> str:
        from app.database.models import Memory, SoulProfile

        base = await self.profile_for_telegram(telegram_id)
        if base.startswith("Сначала") or base.startswith("Профиль"):
            return base

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return base
            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            memories_count = len(
                list(
                    await session.scalars(
                        select(Memory).where(Memory.user_id == user.id, Memory.is_active.is_(True)).limit(100)
                    )
                )
            )

        if profile is None:
            return base

        extra = (
            f"\n\nПол: {profile.gender or '—'}\n"
            f"Семейное положение: {profile.relationship_status or '—'}\n"
            f"Дети: {profile.has_children or '—'}\n"
            f"Сфера: {profile.profession or '—'}\n"
            f"Архетип: {profile.archetype or '—'}\n"
            f"Запомненных важных событий: {memories_count}"
        )
        return f"Мой профиль\n\n{base}{extra}"

    def format_reading_message(self, reading_type: str, question: str, cards: list[dict], interpretation: str) -> str:
        label = READING_TYPE_LABELS.get(reading_type, reading_type)
        card_lines = "\n".join(f"• {card['name']}" for card in cards)
        return (
            f"Расклад: {label}\n"
            f"Вопрос: {question}\n\n"
            f"Карты:\n{card_lines}\n\n"
            f"{interpretation}"
        )

    def interpret_locally(self, question: str, cards: list[dict]) -> str:
        names = ", ".join(card["name"] for card in cards)
        meanings = "; ".join(f"{card['name']}: {card['description']}" for card in cards)
        return (
            f"Вопрос: {question}\n"
            f"Выпали карты: {names}.\n\n"
            f"В эзотерической интерпретации расклад может говорить так: {meanings}. "
            "Главный совет — смотреть не только на внешний знак, но и на то, какой выбор он поднимает внутри тебя."
        )
