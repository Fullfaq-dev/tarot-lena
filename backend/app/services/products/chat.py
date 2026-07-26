"""Open chat for paid Leia users with reading context."""

from __future__ import annotations

import re

from sqlalchemy import select

from app.bot.leia_rich import enrich_ai_prompt, normalize_leia_rich
from app.database.models import ProductUsage
from app.database.session import AsyncSessionLocal
from app.services.ai.kie_client import KieClient
from app.services.products.catalog import PRODUCTS
from app.services.products.entitlements import COMBO_PRODUCTS, EntitlementService
from app.services.products.prompts import leia_menu_navigation_block, leia_reading_system
from app.services.products.service import ProductService

_FOLLOWUP_RE = re.compile(
    r"\b(что|как|почему|зачем|объясни|расскажи|расшифруй|значит|означает|понять|уточни)\b",
    re.IGNORECASE,
)
_NEW_SPREAD_RE = re.compile(
    r"\b("
    r"расклад|"
    r"сделай\s+(?:мне\s+)?(?:расклад|таро|разбор|матриц)|"
    r"новый\s+расклад|"
    r"погадай|"
    r"вытяни\s+карт|"
    r"полный\s+разбор|"
    r"мини[- ]?разбор"
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
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
            )
            return row is not None

    def looks_like_spread_request(self, text: str) -> bool:
        t = text.strip()
        if not t:
            return False
        # «Что значит эта карта?» — обсуждение, не новый расклад.
        if _FOLLOWUP_RE.search(t) and not re.search(
            r"\b(новый|сделай|погадай|вытяни)\b", t, re.IGNORECASE
        ):
            return False
        return bool(_NEW_SPREAD_RE.search(t))

    async def discussable_product_ids(self, user_id: str) -> set[str]:
        """Products the user may discuss in chat (past full or active plan)."""
        ent = EntitlementService()
        if await ent.has_vip(user_id):
            return set(PRODUCTS.keys())

        allowed: set[str] = set()
        if await ent.has_love_plus(user_id):
            allowed.add("love")
        for pid in COMBO_PRODUCTS:
            if await ent.combo_credits(user_id, pid) > 0:
                allowed.add(pid)

        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(ProductUsage.product_id).where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.level == "full",
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
            )
            for (pid,) in rows.all():
                if pid in PRODUCTS:
                    allowed.add(str(pid))
        return allowed

    async def allowed_reading_context(self, user_id: str) -> tuple[str, str | None]:
        """Latest non-empty reading the user is allowed to discuss."""
        allowed = await self.discussable_product_ids(user_id)
        if not allowed:
            return "", None
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage)
                .where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.product_id.in_(allowed),
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
                .order_by(ProductUsage.created_at.desc())
            )
            if row and row.content_preview:
                return row.content_preview, row.product_id
        return "", None

    async def latest_reading(self, user_id: str) -> str:
        text, _ = await self.allowed_reading_context(user_id)
        return text

    async def can_free_spread(self, user_id: str, product_id: str = "tarot_spread") -> bool:
        return await EntitlementService().can_use_full_free(user_id, product_id)

    async def answer_freeform(self, user_id: str, user_name: str, text: str) -> str:
        reading, product_id = await self.allowed_reading_context(user_id)
        allowed = await self.discussable_product_ids(user_id)
        allowed_labels = []
        for pid in sorted(allowed):
            p = PRODUCTS.get(pid)
            if p:
                allowed_labels.append(f"{p.emoji} {p.title}")
        access_line = (
            ", ".join(allowed_labels)
            if allowed_labels
            else "нет оплаченных разборов — только навигация по меню"
        )
        ctx_block = ""
        if reading:
            title = ""
            if product_id and product_id in PRODUCTS:
                p = PRODUCTS[product_id]
                title = f" ({p.emoji} {p.title})"
            ctx_block = f"\n\nКонтекст последнего разрешённого разбора{title}:\n{reading[:3500]}"

        prompt = enrich_ai_prompt(
            f"{leia_menu_navigation_block()}\n\n"
            f"Доступ пользователя к обсуждению разборов: {access_line}.\n\n"
            f"Пользователь {user_name} пишет в чат:\n{text}{ctx_block}\n\n"
            "Ответь как Лея — тепло, на «ты», 4–10 предложений.\n"
            "Если просят новый расклад/матрицу/полный разбор — вежливо откажи "
            "и назови точную кнопку меню (например «🃏 Расклад Таро» или «📦 Пакеты»).\n"
            "Если есть контекст разбора выше — опирайся на него; "
            "не выдумывай новые карты и не начинай новый расклад в чате.\n"
            "Если спрашивают «где найти X» — коротко направь по меню."
        )
        messages = [
            {"role": "system", "content": [{"type": "text", "text": leia_reading_system()}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ]
        text_out = await self.kie.chat_completion(messages)
        return normalize_leia_rich(text_out)
