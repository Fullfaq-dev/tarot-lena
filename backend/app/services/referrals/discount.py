from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Referral, SoulProfile

REFERRED_DISCOUNT_PERCENT = 20
PROMO_NO_PURCHASE_PERCENT = 10
PROMO_NO_PURCHASE_DAYS = 7


def apply_percent_discount(amount: Decimal, percent: int) -> Decimal:
    if percent <= 0:
        return amount
    discounted = amount * (Decimal(100) - Decimal(percent)) / Decimal(100)
    return discounted.quantize(Decimal("1"))


def _promo_percent_from_preferences(preferences: dict | None) -> int:
    if not preferences:
        return 0
    percent = preferences.get("leia_promo_percent")
    until_raw = preferences.get("leia_promo_until")
    if not isinstance(percent, int) or percent <= 0 or not until_raw:
        return 0
    try:
        until = datetime.fromisoformat(str(until_raw))
        if until.tzinfo is None:
            until = until.replace(tzinfo=UTC)
    except ValueError:
        return 0
    if datetime.now(UTC) > until:
        return 0
    return min(int(percent), 50)


async def grant_promo_discount(
    session: AsyncSession,
    user_id: str,
    *,
    percent: int = PROMO_NO_PURCHASE_PERCENT,
    days: int = PROMO_NO_PURCHASE_DAYS,
) -> None:
    profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user_id))
    if profile is None:
        return
    prefs = dict(profile.preferences or {})
    prefs["leia_promo_percent"] = percent
    prefs["leia_promo_until"] = (datetime.now(UTC) + timedelta(days=days)).isoformat()
    profile.preferences = prefs


async def discount_percent_for_user(session: AsyncSession, user_id: str) -> int:
    profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user_id))
    promo = _promo_percent_from_preferences(profile.preferences if profile else None)

    referred = await session.scalar(
        select(Referral.id).where(Referral.referred_user_id == user_id)
    )
    if referred:
        return max(REFERRED_DISCOUNT_PERCENT, promo)
    referrer = await session.scalar(
        select(Referral.id).where(Referral.referrer_user_id == user_id)
    )
    if referrer:
        return max(REFERRED_DISCOUNT_PERCENT, promo)
    return promo
