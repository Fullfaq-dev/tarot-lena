from collections.abc import AsyncIterator

from aiogram.types import User as TelegramUser
from sqlalchemy import select

from app.database.models import Message, MessageRole, User
from app.database.session import AsyncSessionLocal
from app.services.ai.context import ContextBuilder
from app.services.ai.kie_client import KieClient
from app.services.analytics.tracker import track_event
from app.services.billing.service import BillingService
from app.services.billing.tokens import merge_api_usage, provider_cost_rub
from app.services.memory.extractor import MemoryExtractor
from app.services.tarot.service import TarotService


class AIOrchestrator:
    def __init__(self) -> None:
        self.kie = KieClient()
        self.context_builder = ContextBuilder()
        self.billing = BillingService()
        self.memory_extractor = MemoryExtractor()

    async def prepare_chat(
        self, telegram_user: TelegramUser | None, text: str
    ) -> tuple[str | None, list[dict] | None, str | None, str | None, str]:
        if telegram_user is None:
            return None, None, "Не получилось определить профиль Telegram. Попробуй еще раз.", None, "blocked"

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, None, "Сначала нажми /start, чтобы я создала твой профиль.", None, "blocked"

            messages = await self.context_builder.build(session, user)
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
    ) -> dict:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.id == user_id))
            if user is None:
                return {"answer": answer, "charged_rub": "0", "billing_mode": billing_mode}

            chat_api_usage = dict(self.kie.last_usage) if self.kie.last_usage else None
            extraction_usage = await self.memory_extractor.extract_from_dialog(
                session, user, text, answer
            )
            combined_usage = merge_api_usage(chat_api_usage, extraction_usage)

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
                    "model": usage.get("model", "gemini-3-flash"),
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

        chunks: list[str] = []
        async for chunk in self.stream_chat(messages or []):
            chunks.append(chunk)
        answer = "".join(chunks).strip() or "Не удалось получить ответ. Попробуй ещё раз."
        result = await self.complete_chat(
            user_id or "",
            text,
            answer,
            user_message_id=user_message_id,
            context_messages=messages,
            billing_mode=billing_mode,
        )
        return result.get("answer", answer)

    async def prepare_tarot_reading(
        self,
        telegram_user: TelegramUser | None,
        question: str,
        cards: list[dict],
        reading_type: str,
    ) -> tuple[str | None, list[dict] | None, str | None, str | None, str]:
        if telegram_user is None:
            return None, None, "Не получилось определить профиль Telegram. Попробуй еще раз.", None, "blocked"

        card_lines = "\n".join(f"- {card['name']}: {card['description']}" for card in cards)
        reading_prompt = (
            f"Сделай краткое толкование расклада Таро (до 5 предложений).\n"
            f"Тип: {reading_type}\n"
            f"Вопрос: {question}\n"
            f"Карты:\n{card_lines}\n"
            "Свяжи с вопросом и дай один практический совет."
        )

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, None, "Сначала нажми /start, чтобы я создала твой профиль.", None, "blocked"

            messages = await self.context_builder.build(session, user)
            messages.append({"role": "user", "content": [{"type": "text", "text": reading_prompt}]})

            allowed, reason, billing_mode = await self.billing.ensure_can_use_chat(
                session, user, context_messages=messages
            )
            if not allowed:
                return None, None, reason, None, billing_mode

            billing_mode = await self.billing.reserve_chat_slot(session, user, billing_mode)

            user_message = Message(user_id=user.id, role=MessageRole.USER.value, content=question)
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

        chunks: list[str] = []
        async for chunk in self.stream_chat(messages or []):
            chunks.append(chunk)
        answer = "".join(chunks).strip()
        if not answer or "cannot fulfill" in answer.lower():
            answer = TarotService().interpret_locally(question, cards)

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
