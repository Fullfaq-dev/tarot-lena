"""Open chat for paid Leia users with reading context."""

from __future__ import annotations

import re

from sqlalchemy import select

from app.bot.leia_rich import enrich_ai_prompt, normalize_leia_rich
from app.database.models import ProductUsage
from app.database.session import AsyncSessionLocal
from app.services.ai.kie_client import KieClient
from app.services.products.entitlements import EntitlementService
from app.services.products.prompts import leia_reading_system
from app.services.products.service import ProductService

_FOLLOWUP_RE = re.compile(
    r"\b(что|как|почему|зачем|объясни|расскажи|расшифруй|значит|означает|понять|уточни)\b",
    re.IGNORECASE,
)
_NEW_SPREAD_RE = re.compile(
    r"\b("
    r"расклад|"
    r"сделай\s+(?:мне\s+)?(?:расклад|таро)|"
    r"новый\s+расклад|"
    r"погадай|"
    r"вытяни\s+карт"
    r")\b",
    re.IGNORECASE,
)


class LeiaChatService:
    def __init__(self) -> None:
        self.kie = KieClient()

    async def has_open_chat(self, user_id: str) -> bool:
        ent = EntitlementService()
        if await ent.has_vip(user_id) or await ent.has_love_plus(user_id):
            return True
        if await ent.has_any_plan(user_id):
            return True
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage.id).where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.level == "full",
                )
            )
            return row is not None

    def looks_like_spread_request(self, text: str) -> bool:
        t = text.strip()
        if not t:
            return False
        # «Что значит эта карта?» — обсуждение, не новый расклад.
        if _FOLLOWUP_RE.search(t):
            return False
        return bool(_NEW_SPREAD_RE.search(t))

    async def latest_reading(self, user_id: str) -> str:
        return await ProductService().latest_reading_context(user_id)

    async def can_free_spread(self, user_id: str, product_id: str = "tarot_spread") -> bool:
        return await EntitlementService().can_use_full_free(user_id, product_id)

    async def answer_freeform(self, user_id: str, user_name: str, text: str) -> str:
        reading = await ProductService().latest_reading_context(user_id)
        ctx_block = ""
        if reading:
            ctx_block = f"\n\nКонтекст последнего разбора:\n{reading[:3500]}"
        prompt = enrich_ai_prompt(
            f"Пользователь {user_name} пишет в чат:\n{text}{ctx_block}\n\n"
            "Ответь как Лея — тепло, на «ты», 4–10 предложений. "
            "Опирайся на разбор выше, если он есть. "
            "Не начинай новый полный расклад в чате — если просят новую тему из меню, "
            "кратко ответь и предложи выбрать продукт в меню."
        )
        messages = [
            {"role": "system", "content": [{"type": "text", "text": leia_reading_system()}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ]
        text_out = await self.kie.chat_completion(messages)
        return normalize_leia_rich(text_out)
