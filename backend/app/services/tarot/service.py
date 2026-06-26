import random
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import func, select

from app.database.models import DailyPrediction, Message, MessageRole, TarotCard, TarotReading, User
from app.database.session import AsyncSessionLocal
from app.core.config import get_settings
from app.services.billing.limits import FREE_READINGS_PER_MONTH, HISTORY_PAGE_SIZE
from app.services.billing.limits import is_unlimited_chat
from app.services.billing.service import BillingService
from app.services.billing.tokens import format_balance
from app.services.ai.context import ContextBuilder
from app.services.ai.kie_client import KieClient
from app.services.tarot.cards import FULL_DECK, storage_image_path
from app.services.tarot.daily_card import pick_daily_card_with_ai
from app.bot.i18n import SUPPORTED_LANGUAGES, normalize_language, reading_label, t
from app.services.settings.service import SettingsService

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

    async def menu_text(self, selected: str, lang: str = "ru") -> str:
        if selected == t("btn_history", lang):
            return t("history_empty", lang)
        return t("readings_menu_text", lang)

    async def _lang(self, telegram_id: int) -> str:
        return await SettingsService().get_ui_language(telegram_id)

    async def daily_card_for_telegram(self, telegram_id: int) -> tuple[str, dict | None]:
        lang = await self._lang(telegram_id)
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", lang), None

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
                if card is not None and self._daily_text_matches_language(existing.text, lang):
                    return existing.text, card
                await session.delete(existing)
                await session.flush()

            messages = await self.context_builder.build(
                session, user, user_query=t("tarot_daily_query", lang)
            )
            try:
                picked, interpretation = await pick_daily_card_with_ai(messages, self.kie, lang=lang)
            except ValueError:
                picked = self.draw_cards(1)[0]
                interpretation = t(
                    "tarot_daily_fallback",
                    lang,
                    name=picked["name"],
                    description=picked["description"],
                )

            card = self._attach_image_path(picked)
            text = interpretation.strip()
            if not text.startswith(t("tarot_daily_card_header_prefix", lang)):
                text = t("tarot_daily_card_header", lang, name=card["name"], text=text)

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

    async def record_daily_card_context(
        self, telegram_id: int, interpretation: str, *, card_name: str
    ) -> None:
        lang = await self._lang(telegram_id)
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return

            recent = await session.scalars(
                select(Message)
                .where(Message.user_id == user.id)
                .order_by(Message.created_at.desc())
                .limit(4)
            )
            today = date.today().isoformat()
            for msg in recent:
                if isinstance(msg.meta, dict) and msg.meta.get("feature") == "daily_card":
                    if msg.meta.get("prediction_date") == today:
                        return

            session.add(
                Message(
                    user_id=user.id,
                    role=MessageRole.USER.value,
                    content=t("tarot_daily_context_msg", lang),
                )
            )
            session.add(
                Message(
                    user_id=user.id,
                    role=MessageRole.ASSISTANT.value,
                    content=interpretation.strip(),
                    meta={
                        "feature": "daily_card",
                        "card": card_name,
                        "prediction_date": today,
                    },
                )
            )
            await session.commit()

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
    def _is_stale_daily_text(text: str, lang: str = "ru") -> bool:
        return t("tarot_daily_stale_marker", lang) in text

    @staticmethod
    def _daily_text_matches_language(text: str, lang: str = "ru") -> bool:
        """Avoid reusing today's daily card if it was cached in another UI language."""
        current_lang = normalize_language(lang)
        for supported in SUPPORTED_LANGUAGES:
            header = t("tarot_daily_card_header_prefix", supported)
            marker = t("tarot_daily_stale_marker", supported)
            if header in text or marker in text:
                return supported == current_lang
        return current_lang == "ru"

    @staticmethod
    def _today_start_utc() -> datetime:
        now = datetime.now(UTC)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    async def _subscription_tier(self, session, user: User) -> str:
        from app.database.models import Subscription

        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        return subscription.tier if subscription else "free"

    async def ensure_can_read_today(self, telegram_id: int) -> tuple[bool, str | None]:
        lang = await self._lang(telegram_id)
        billing = BillingService()
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return False, t("error_need_start", lang)

            await billing.sync_free_limits_month(session, user)
            tier = await self._subscription_tier(session, user)
            if is_unlimited_chat(tier):
                return True, None

            if user.free_readings_used_month < FREE_READINGS_PER_MONTH:
                return True, None

            allowed, reason, _ = await billing.ensure_can_use_chat(
                session,
                user,
                allow_free_slot=False,
            )
            if allowed:
                return True, None
            return False, t(
                "tarot_readings_monthly_limit",
                lang,
                limit=FREE_READINGS_PER_MONTH,
                balance=format_balance(user.balance_rub),
            )

    async def readings_left_today(self, telegram_id: int) -> int:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return 0
            billing = BillingService()
            await billing.sync_free_limits_month(session, user)
            tier = await self._subscription_tier(session, user)
            if is_unlimited_chat(tier):
                return FREE_READINGS_PER_MONTH
            return max(0, FREE_READINGS_PER_MONTH - user.free_readings_used_month)

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
        self, telegram_id: int, page: int = 0, *, lang: str | None = None
    ) -> tuple[str, list[TarotReading], int, int]:
        from app.bot.i18n import reading_label

        lang = lang or await self._lang(telegram_id)
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", lang), [], 0, 0

            total = await session.scalar(
                select(func.count())
                .select_from(TarotReading)
                .where(TarotReading.user_id == user.id)
            )
            total = int(total or 0)
            if total == 0:
                return t("history_empty", lang), [], 0, 0

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

            table_rows: list[list[str]] = []
            for index, reading in enumerate(items, start=offset + 1):
                label = reading_label(reading.reading_type, lang)
                question = reading.question[:60] + ("…" if len(reading.question) > 60 else "")
                table_rows.append([str(index), label, f"«{question}»"])

            from app.bot.rich_layouts import format_reading_history_rich

            text = format_reading_history_rich(
                lang=lang,
                page_label=t("history_page", lang, page=page + 1, total=total_pages),
                hint=t("history_hint", lang),
                rows=table_rows,
            )
            return text, items, page, total_pages

    async def history_entries(self, telegram_id: int) -> tuple[str, list[TarotReading]]:
        text, items, _, _ = await self.history_page(telegram_id, page=0)
        return text, items

    async def history_for_telegram(self, telegram_id: int) -> str:
        text, _ = await self.history_entries(telegram_id)
        return text

    async def reading_detail_for_telegram(self, telegram_id: int, reading_id: str) -> str | None:
        lang = await self._lang(telegram_id)
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
                lang,
            )

    async def profile_for_telegram(self, telegram_id: int) -> str:
        from app.database.models import SoulProfile

        lang = await self._lang(telegram_id)
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", lang)

            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            if profile is None:
                return t("profile_not_collected", lang)

            birth_date = (
                profile.birth_date.strftime("%d.%m.%Y")
                if profile.birth_date
                else t("profile_not_specified", lang)
            )
            lines = [
                t("profile_line", lang, label=t("profile_summary_name", lang), value=profile.name or "—"),
                t("profile_line", lang, label=t("profile_summary_birth", lang), value=birth_date),
                t("profile_line", lang, label=t("profile_summary_time", lang), value=profile.birth_time or "—"),
                t("profile_line", lang, label=t("profile_summary_city", lang), value=profile.birth_city or "—"),
                t("profile_line", lang, label=t("profile_summary_goal", lang), value=profile.six_month_goal or "—"),
                t("profile_line", lang, label=t("profile_summary_concern", lang), value=profile.main_concern or "—"),
                t("profile_line", lang, label=t("profile_summary_belief", lang), value=profile.belief_system or "—"),
            ]
            return "\n".join(lines)

    async def profile_extended_for_telegram(self, telegram_id: int) -> str:
        from app.database.models import Memory, SoulProfile

        lang = await self._lang(telegram_id)
        base = await self.profile_for_telegram(telegram_id)
        if base == t("error_need_start", lang) or base == t("profile_not_collected", lang):
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

        extra_lines = [
            t("profile_line", lang, label=t("profile_summary_gender", lang), value=profile.gender or "—"),
            t("profile_line", lang, label=t("profile_summary_relationship", lang), value=profile.relationship_status or "—"),
            t("profile_line", lang, label=t("profile_summary_children", lang), value=profile.has_children or "—"),
            t("profile_line", lang, label=t("profile_summary_profession", lang), value=profile.profession or "—"),
            t("profile_line", lang, label=t("profile_summary_archetype", lang), value=profile.archetype or "—"),
            t("profile_summary_memories", lang, count=memories_count),
        ]
        status_block = await BillingService().profile_status_block(telegram_id)
        if status_block:
            extra_lines.append("")
            extra_lines.append(status_block)
        extra = "\n\n" + "\n".join(extra_lines)
        return t("profile_title", lang, base=base, extra=extra)

    def format_reading_message(
        self, reading_type: str, question: str, cards: list[dict], interpretation: str, lang: str = "ru"
    ) -> str:
        label = reading_label(reading_type, lang)
        card_lines = "\n".join(f"• {card['name']}" for card in cards)
        return t(
            "reading_format_header",
            lang,
            label=label,
            question=question,
            cards=card_lines,
            interpretation=interpretation,
        )

    def interpret_locally(self, question: str, cards: list[dict], lang: str = "ru") -> str:
        names = ", ".join(card["name"] for card in cards)
        meanings = "; ".join(f"{card['name']}: {card['description']}" for card in cards)
        return t("tarot_local_interpretation", lang, question=question, names=names, meanings=meanings)
