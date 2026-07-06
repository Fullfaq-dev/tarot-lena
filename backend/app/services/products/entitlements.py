import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ProductEntitlement, Subscription
from app.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

SUBSCRIPTION_DAYS = 30
COMBO_PRODUCTS = ("love", "wealth", "forecast")


class EntitlementService:
    async def _active_rows(self, session: AsyncSession, user_id: str) -> list[ProductEntitlement]:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(ProductEntitlement).where(
                ProductEntitlement.user_id == user_id,
                or_(
                    ProductEntitlement.expires_at.is_(None),
                    ProductEntitlement.expires_at > now,
                ),
            )
        )
        rows = list(result.scalars().all())
        return [r for r in rows if r.uses_remaining is None or r.uses_remaining > 0]

    async def has_vip(self, user_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            rows = await self._active_rows(session, user_id)
            return any(r.kind == "vip" for r in rows)

    async def has_love_plus(self, user_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            rows = await self._active_rows(session, user_id)
            return any(r.kind == "love_plus" for r in rows)

    async def combo_credits(self, user_id: str, product_id: str) -> int:
        kind = f"combo_{product_id}"
        async with AsyncSessionLocal() as session:
            rows = await self._active_rows(session, user_id)
            total = 0
            for row in rows:
                if row.kind == kind:
                    total += row.uses_remaining or 0
            return total

    async def can_use_full_free(self, user_id: str, product_id: str) -> bool:
        if await self.has_vip(user_id):
            return True
        if product_id == "love" and await self.has_love_plus(user_id):
            return True
        if product_id in COMBO_PRODUCTS:
            return await self.combo_credits(user_id, product_id) > 0
        return False

    async def full_access_label(self, user_id: str, product_id: str) -> str | None:
        if await self.has_vip(user_id):
            return "VIP"
        if product_id == "love" and await self.has_love_plus(user_id):
            return "ЛЮБОВЬ+"
        if product_id in COMBO_PRODUCTS:
            credits = await self.combo_credits(user_id, product_id)
            if credits > 0:
                return f"пакет · {credits} шт."
        return None

    async def has_any_plan(self, user_id: str) -> bool:
        return await self.active_plan_label(user_id) is not None

    async def active_plan_label(self, user_id: str) -> str | None:
        if await self.has_vip(user_id):
            return "👑 VIP активен"
        if await self.has_love_plus(user_id):
            return "💗 ЛЮБОВЬ+ активна"
        labels = {
            "love": "💞",
            "wealth": "💰",
            "forecast": "📆",
        }
        parts = []
        for pid in COMBO_PRODUCTS:
            n = await self.combo_credits(user_id, pid)
            if n:
                parts.append(f"{labels[pid]}×{n}")
        if parts:
            return f"🎁 Комбо: {' '.join(parts)}"
        return None

    async def grant_combo_happy_woman(
        self, session: AsyncSession, user_id: str, payment_id: str
    ) -> None:
        for product_id in COMBO_PRODUCTS:
            session.add(
                ProductEntitlement(
                    user_id=user_id,
                    kind=f"combo_{product_id}",
                    uses_remaining=1,
                    source_payment_id=payment_id,
                )
            )

    async def grant_subscription(
        self,
        session: AsyncSession,
        user_id: str,
        kind: str,
        payment_id: str,
    ) -> None:
        expires = datetime.now(timezone.utc) + timedelta(days=SUBSCRIPTION_DAYS)
        session.add(
            ProductEntitlement(
                user_id=user_id,
                kind=kind,
                expires_at=expires,
                uses_remaining=None,
                source_payment_id=payment_id,
            )
        )
        subscription = await session.scalar(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        if subscription is None:
            subscription = Subscription(user_id=user_id)
            session.add(subscription)
            await session.flush()
        subscription.tier = kind
        subscription.status = "active"
        subscription.started_at = datetime.now(timezone.utc)
        subscription.expires_at = expires
        subscription.provider = "platega"
        subscription.provider_subscription_id = payment_id

    async def consume_credit(
        self, session: AsyncSession, user_id: str, product_id: str
    ) -> None:
        rows = await self._active_rows(session, user_id)
        if any(r.kind == "vip" for r in rows):
            return
        if product_id == "love" and any(r.kind == "love_plus" for r in rows):
            return
        kind = f"combo_{product_id}"
        for row in rows:
            if row.kind == kind and row.uses_remaining and row.uses_remaining > 0:
                row.uses_remaining -= 1
                return
