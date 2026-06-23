from collections.abc import AsyncIterator

from aiogram.types import User as TelegramUser
from sqlalchemy import select

from app.database.models import Message, MessageRole, User
from app.database.session import AsyncSessionLocal
from app.services.ai.context import ContextBuilder
from app.services.ai.kie_client import KieClient
from app.services.analytics.tracker import track_event
from app.services.billing.service import BillingService
from app.services.billing.limits import FREE_READINGS_PER_MONTH
from app.services.billing.tokens import merge_api_usage, provider_cost_rub
from app.services.memory.extractor import MemoryExtractor
from app.services.energy.service import BraceletSlot, DrawnRune, EnergyService
from app.services.energy.localize import localize_rune
from app.services.energy.stone_picker import pick_bracelet_layout_with_ai, pick_stones_with_ai
from app.services.energy.catalog import RUNE_BY_SLUG, Stone
from app.services.zen.service import ZenService
from app.bot.i18n import normalize_language, t
from app.bot.i18n_ai import (
    bracelet_ai_prompt,
    bracelet_stored_user,
    rune_ai_prompt,
    rune_stored_user,
    stone_ai_prompt,
    stone_stored_user,
    tarot_ai_prompt,
    tarot_stored_user,
    zen_ai_prompt,
    zen_stored_user,
)
from app.database.models import UserSettings
from app.services.tarot.service import READING_TYPE_LABELS, TarotService


class AIOrchestrator:
    def __init__(self) -> None:
        self.kie = KieClient()
        self.context_builder = ContextBuilder()
        self.billing = BillingService()
        self.memory_extractor = MemoryExtractor()

    async def _user_lang(self, session, user_id: str) -> str:
        settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user_id))
        return normalize_language(settings.ui_language if settings else None)

    async def prepare_chat(
        self, telegram_user: TelegramUser | None, text: str
    ) -> tuple[str | None, list[dict] | None, str | None, str | None, str]:
        lang = normalize_language(telegram_user.language_code if telegram_user else None)
        if telegram_user is None:
            return None, None, t("error_telegram_profile", lang), None, "blocked"

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, None, t("error_need_start", lang), None, "blocked"
            lang = await self._user_lang(session, user.id)

            messages = await self.context_builder.build(session, user, user_query=text)
            messages.append({"role": "user", "content": [{"type": "text", "text": text}]})

            allowed, reason, billing_mode = await self.billing.ensure_can_use_chat(
                session, user, context_messages=messages
            )
            if not allowed:
                return None, None, reason, None, billing_mode

            billing_mode = await self.billing.reserve_chat_slot(session, user, billing_mode)

            user_message = Message(user_id=user.id, role=MessageRole.USER.value, content=text)
            session.add(user_message)
            await session.flush()
            await session.commit()
            return user.id, messages, None, user_message.id, billing_mode

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        async for chunk in self.kie.stream_chat(messages):
            yield chunk

    async def generate_chat(self, messages: list[dict], lang: str = "en") -> str:
        answer = await self.kie.chat_completion(messages)
        return answer.strip() or t("error_no_ai_response", lang)

    async def complete_chat(
        self,
        user_id: str,
        text: str,
        answer: str,
        *,
        user_message_id: str | None = None,
        context_messages: list[dict] | None = None,
        feature: str = "chat",
        billing_mode: str = "free",
        extra_api_usage: dict[str, int] | None = None,
    ) -> dict:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.id == user_id))
            if user is None:
                return {"answer": answer, "charged_rub": "0", "billing_mode": billing_mode}

            chat_api_usage = dict(self.kie.last_usage) if self.kie.last_usage else None
            extraction_usage = await self.memory_extractor.extract_from_dialog(
                session, user, text, answer
            )
            combined_usage = merge_api_usage(chat_api_usage, extraction_usage, extra_api_usage)

            usage_meta: dict = {}
            if chat_api_usage:
                usage_meta["chat_input_tokens"] = chat_api_usage.get("input_tokens", 0)
                usage_meta["chat_output_tokens"] = chat_api_usage.get("output_tokens", 0)
            if extraction_usage:
                usage_meta["memory_extraction_ran"] = True
                usage_meta["memory_extraction_input_tokens"] = extraction_usage.get("input_tokens", 0)
                usage_meta["memory_extraction_output_tokens"] = extraction_usage.get("output_tokens", 0)

            usage = await self.billing.record_chat_usage(
                session,
                user,
                text,
                answer,
                feature=feature,
                context_messages=context_messages,
                api_usage=combined_usage,
                billing_mode=billing_mode,
                extra_meta=usage_meta,
            )

            if user_message_id:
                user_message = await session.scalar(
                    select(Message).where(Message.id == user_message_id, Message.user_id == user.id)
                )
                if user_message:
                    user_message.tokens_input = usage["question_tokens"]
                    user_message.meta = {
                        "exchange": True,
                        "context_tokens": usage["input_tokens"],
                        "billing_mode": billing_mode,
                    }

            assistant_message = Message(
                user_id=user.id,
                role=MessageRole.ASSISTANT.value,
                content=answer,
                tokens_input=usage["input_tokens"],
                tokens_output=usage["output_tokens"],
                cost_rub=usage["charged_rub"],
                meta={
                    "question_tokens": usage["question_tokens"],
                    "answer_tokens": usage["answer_tokens"],
                    "provider_cost_usd": str(usage["provider_cost_usd"]),
                    "provider_cost_rub": str(
                        provider_cost_rub(usage["input_tokens"], usage["output_tokens"])
                    ),
                    "model": usage.get("model", "gpt-5-2"),
                    "usage_record_id": usage["usage_record_id"],
                    "billing_mode": billing_mode,
                    "cost_source": "kie_api" if combined_usage else "estimated",
                    "memory_extraction_ran": bool(extraction_usage),
                },
            )
            session.add(assistant_message)
            await session.commit()
            await track_event(
                "bot.ai_response",
                user_id=user.id,
                payload={
                    "input_tokens": usage["input_tokens"],
                    "output_tokens": usage["output_tokens"],
                    "charged_rub": str(usage["charged_rub"]),
                    "billing_mode": billing_mode,
                },
            )
            usage["answer"] = answer
            return usage

    async def answer_text(self, telegram_user: TelegramUser | None, text: str) -> str:
        user_id, messages, error, user_message_id, billing_mode = await self.prepare_chat(
            telegram_user, text
        )
        if error:
            return error

        answer = await self.generate_chat(messages or [])
        result = await self.complete_chat(
            user_id or "",
            text,
            answer,
            user_message_id=user_message_id,
            context_messages=messages,
            billing_mode=billing_mode,
        )
        return result.get("answer", answer)

    def _inject_system_addon(self, messages: list[dict], addon: str) -> list[dict]:
        if not messages or messages[0].get("role") != "system":
            return messages
        updated = list(messages)
        first = dict(updated[0])
        content = first.get("content") or []
        if content and isinstance(content[0], dict):
            text = content[0].get("text", "")
            content = [{"type": "text", "text": f"{text}\n\n{addon}"}]
        first["content"] = content
        updated[0] = first
        return updated

    async def _prepare_billed_exchange(
        self,
        telegram_user: TelegramUser | None,
        *,
        user_query: str,
        ai_prompt: str,
        stored_user_text: str,
    ) -> tuple[str | None, list[dict] | None, str | None, str | None, str]:
        lang = normalize_language(telegram_user.language_code if telegram_user else None)
        if telegram_user is None:
            return None, None, t("error_telegram_profile", lang), None, "blocked"

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, None, t("error_need_start", lang), None, "blocked"
            lang = await self._user_lang(session, user.id)

            messages = await self.context_builder.build(session, user, user_query=user_query)
            messages.append({"role": "user", "content": [{"type": "text", "text": ai_prompt}]})

            allowed, reason, billing_mode = await self.billing.ensure_can_use_chat(
                session, user, context_messages=messages
            )
            if not allowed:
                return None, None, reason, None, billing_mode

            billing_mode = await self.billing.reserve_chat_slot(session, user, billing_mode)
            user_message = Message(
                user_id=user.id, role=MessageRole.USER.value, content=stored_user_text
            )
            session.add(user_message)
            await session.flush()
            await session.commit()
            return user.id, messages, None, user_message.id, billing_mode

    async def _resolve_lang(self, telegram_user: TelegramUser | None, hint: str = "en") -> str:
        if telegram_user is None:
            return normalize_language(hint)
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return normalize_language(telegram_user.language_code or hint)
            return await self._user_lang(session, user.id)

    async def prepare_zen_reflection(
        self,
        telegram_user: TelegramUser | None,
        text: str,
        *,
        lang: str = "ru",
    ) -> tuple[str | None, list[dict] | None, str | None, str | None, str]:
        resolved_lang = await self._resolve_lang(telegram_user, lang)
        zen = ZenService()
        addon = zen.load_zen_prompt(resolved_lang)
        user_id, messages, error, msg_id, billing = await self._prepare_billed_exchange(
            telegram_user,
            user_query=text,
            ai_prompt=zen_ai_prompt(resolved_lang, text),
            stored_user_text=zen_stored_user(resolved_lang, text),
        )
        if error or not messages:
            return user_id, messages, error, msg_id, billing
        return user_id, self._inject_system_addon(messages, addon), None, msg_id, billing

    async def prepare_rune_reading(
        self,
        telegram_user: TelegramUser | None,
        question: str,
        drawn: list[DrawnRune],
        *,
        lang: str = "ru",
    ) -> tuple[str | None, list[dict] | None, str | None, str | None, str]:
        resolved_lang = await self._resolve_lang(telegram_user, lang)
        energy = EnergyService()
        rune_lines = energy.rune_lines_for_ai(drawn, resolved_lang)
        names = ", ".join(localize_rune(d.rune, resolved_lang).name for d in drawn)
        return await self._prepare_billed_exchange(
            telegram_user,
            user_query=question,
            ai_prompt=rune_ai_prompt(resolved_lang, question, rune_lines),
            stored_user_text=rune_stored_user(resolved_lang, question, names),
        )

    async def prepare_stone_reading(
        self,
        telegram_user: TelegramUser | None,
        query: str,
        *,
        lang: str = "ru",
    ) -> tuple[
        str | None,
        list[Stone],
        str,
        list[dict] | None,
        str | None,
        str | None,
        str,
        dict[str, int] | None,
    ]:
        lang = normalize_language(telegram_user.language_code if telegram_user else None)
        if telegram_user is None:
            return None, [], "", None, t("error_telegram_profile", lang), None, "blocked", None

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, [], "", None, t("error_need_start", lang), None, "blocked", None
            lang = await self._user_lang(session, user.id)

            base_messages = await self.context_builder.build(session, user, user_query=query)
            pick_usage: dict[str, int] | None = None
            pick_reason = ""

            try:
                stones, pick_reason = await pick_stones_with_ai(base_messages, self.kie, query, lang)
                pick_usage = dict(self.kie.last_usage) if self.kie.last_usage else None
            except ValueError:
                stones = EnergyService().recommend_stones(query)

            energy = EnergyService()
            stone_lines = energy.stone_lines_for_ai(stones, lang)
            ai_prompt = stone_ai_prompt(lang, query, stone_lines, pick_reason)

            messages = list(base_messages)
            messages.append({"role": "user", "content": [{"type": "text", "text": ai_prompt}]})

            allowed, reason, billing_mode = await self.billing.ensure_can_use_chat(
                session, user, context_messages=messages
            )
            if not allowed:
                return None, stones, pick_reason, None, reason, None, billing_mode, pick_usage

            billing_mode = await self.billing.reserve_chat_slot(session, user, billing_mode)
            names = ", ".join(s.name for s in stones)
            stored = stone_stored_user(lang, query, names)
            user_message = Message(user_id=user.id, role=MessageRole.USER.value, content=stored)
            session.add(user_message)
            await session.flush()
            await session.commit()
            return user.id, stones, pick_reason, messages, None, user_message.id, billing_mode, pick_usage

    async def prepare_bracelet_reading(
        self,
        telegram_user: TelegramUser | None,
        query: str,
        *,
        lang: str = "ru",
    ) -> tuple[
        str | None,
        list[BraceletSlot],
        str,
        list[dict] | None,
        str | None,
        str | None,
        str,
        dict[str, int] | None,
    ]:
        lang = normalize_language(telegram_user.language_code if telegram_user else None)
        if telegram_user is None:
            return None, [], "", None, t("error_telegram_profile", lang), None, "blocked", None

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, [], "", None, t("error_need_start", lang), None, "blocked", None
            lang = await self._user_lang(session, user.id)

            base_messages = await self.context_builder.build(session, user, user_query=query)
            pick_usage: dict[str, int] | None = None
            pick_reason = ""
            energy = EnergyService()

            try:
                layout, rune_slug, pick_reason = await pick_bracelet_layout_with_ai(
                    base_messages, self.kie, query, lang
                )
                pick_usage = dict(self.kie.last_usage) if self.kie.last_usage else None
                slots = energy.build_bracelet_from_layout(layout, RUNE_BY_SLUG[rune_slug], lang)
            except (ValueError, KeyError):
                slots = energy.build_bracelet(query, lang)

            layout_lines = energy.bracelet_lines_for_ai(slots, lang)
            ai_prompt = bracelet_ai_prompt(lang, query, layout_lines, pick_reason)

            messages = list(base_messages)
            messages.append({"role": "user", "content": [{"type": "text", "text": ai_prompt}]})

            allowed, reason, billing_mode = await self.billing.ensure_can_use_chat(
                session, user, context_messages=messages
            )
            if not allowed:
                return None, slots, pick_reason, None, reason, None, billing_mode, pick_usage

            billing_mode = await self.billing.reserve_chat_slot(session, user, billing_mode)
            stored = bracelet_stored_user(lang, query)
            user_message = Message(user_id=user.id, role=MessageRole.USER.value, content=stored)
            session.add(user_message)
            await session.flush()
            await session.commit()
            return user.id, slots, pick_reason, messages, None, user_message.id, billing_mode, pick_usage

    async def prepare_tarot_reading(
        self,
        telegram_user: TelegramUser | None,
        question: str,
        cards: list[dict],
        reading_type: str,
    ) -> tuple[str | None, list[dict] | None, str | None, str | None, str]:
        lang = normalize_language(telegram_user.language_code if telegram_user else None)
        if telegram_user is None:
            return None, None, t("error_telegram_profile", lang), None, "blocked"

        card_lines = "\n".join(f"- {card['name']}: {card['description']}" for card in cards)
        from app.bot.i18n import reading_label

        label = reading_label(reading_type, lang)
        reading_prompt = tarot_ai_prompt(lang, reading_type, question, card_lines)
        stored_user_text = tarot_stored_user(
            lang, label, question, ", ".join(card["name"] for card in cards)
        )

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, None, t("error_need_start", lang), None, "blocked"

            messages = await self.context_builder.build(session, user, user_query=question)
            messages.append({"role": "user", "content": [{"type": "text", "text": reading_prompt}]})

            await self.billing.sync_free_limits_month(session, user)
            readings_exhausted = user.free_readings_used_month >= FREE_READINGS_PER_MONTH

            allowed, reason, billing_mode = await self.billing.ensure_can_use_chat(
                session,
                user,
                context_messages=messages,
                allow_free_slot=not readings_exhausted,
            )
            if not allowed:
                return None, None, reason, None, billing_mode

            billing_mode = await self.billing.reserve_chat_slot(session, user, billing_mode)
            billing_mode = await self.billing.reserve_reading_slot(session, user, billing_mode)

            user_message = Message(user_id=user.id, role=MessageRole.USER.value, content=stored_user_text)
            session.add(user_message)
            await session.flush()
            await session.commit()
            return user.id, messages, None, user_message.id, billing_mode

    async def answer_tarot_reading(
        self,
        telegram_user: TelegramUser | None,
        question: str,
        cards: list[dict],
        reading_type: str,
    ) -> str:
        user_id, messages, error, user_message_id, billing_mode = await self.prepare_tarot_reading(
            telegram_user, question, cards, reading_type
        )
        if error:
            return error

        answer = await self.generate_chat(messages or [])
        if not answer or "cannot fulfill" in answer.lower():
            lang = await self._resolve_lang(telegram_user)
            answer = TarotService().interpret_locally(question, cards, lang)

        result = await self.complete_chat(
            user_id or "",
            question,
            answer,
            user_message_id=user_message_id,
            context_messages=messages,
            feature="tarot_reading",
            billing_mode=billing_mode,
        )
        return result.get("answer", answer)
