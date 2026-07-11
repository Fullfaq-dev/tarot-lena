from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Referral

REFERRED_DISCOUNT_PERCENT = 20


def apply_percent_discount(amount: Decimal, percent: int) -> Decimal:
    if percent <= 0:
        return amount
    discounted = amount * (Decimal(100) - Decimal(percent)) / Decimal(100)
    return discounted.quantize(Decimal("1"))


async def discount_percent_for_user(session: AsyncSession, user_id: str) -> int:
    referral = await session.scalar(
        select(Referral.id).where(Referral.referred_user_id == user_id)
    )
    return REFERRED_DISCOUNT_PERCENT if referral else 0
