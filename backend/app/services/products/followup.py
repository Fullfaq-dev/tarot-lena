from app.bot.leia_rich import enrich_ai_prompt, normalize_leia_rich
from app.services.ai.kie_client import KieClient
from app.services.dialog_log import log_dialog_exchange
from app.services.products.prompts import numerology_system


class ReadingFollowupService:
    def __init__(self) -> None:
        self.kie = KieClient()

    async def answer(
        self,
        *,
        reading_excerpt: str,
        question: str,
        user_name: str,
        user_id: str | None = None,
    ) -> str:
        prompt = enrich_ai_prompt(
            f"Пользователь {user_name} получил разбор от Леи:\n\n"
            f"{reading_excerpt[:3500]}\n\n"
            f"Вопрос к разбору: {question}\n\n"
            "Ответь как Лея — тепло, по делу, 4–8 предложений. "
            "Опирайся на разбор выше, не выдумывай новый расклад."
        )
        messages = [
            {"role": "system", "content": [{"type": "text", "text": numerology_system()}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ]
        text = await self.kie.chat_completion(messages)
        answer = normalize_leia_rich(text)
        if user_id:
            from app.services.billing.usage_log import record_kie_usage

            await record_kie_usage(
                user_id,
                feature="reading_followup",
                question=question,
                answer=answer,
                api_usage=self.kie.last_usage,
            )
            await log_dialog_exchange(
                user_id,
                question,
                answer,
                source="reading_followup",
            )
        return answer
