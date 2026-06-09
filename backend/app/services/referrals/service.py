from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Referral, ReferralWithdrawalRequest, User

MIN_WITHDRAWAL_RUB = Decimal("3000")


class ReferralService:
    async def attach_referrer(
        self, session: AsyncSession, referrer: User, referred: User
    ) -> Referral | None:
        if referrer.id == referred.id:
            return None
        existing = await session.scalar(
            select(Referral).where(Referral.referred_user_id == referred.id)
        )
        if existing:
            return existing
        referral = Referral(referrer_user_id=referrer.id, referred_user_id=referred.id)
        session.add(referral)
        return referral

    async def accrue_reward(
        self, session: AsyncSession, referred_user_id: str, payment_amount: Decimal
    ) -> None:
        referral = await session.scalar(
            select(Referral).where(Referral.referred_user_id == referred_user_id)
        )
        if referral is None:
            return
        referral.accrued_rub += payment_amount * Decimal(referral.reward_percent) / Decimal("100")

    async def request_withdrawal(
        self, session: AsyncSession, user: User, amount: Decimal, details: dict
    ) -> ReferralWithdrawalRequest:
        if amount < MIN_WITHDRAWAL_RUB:
            raise ValueError("Минимальная сумма вывода — 3000 рублей.")
        request = ReferralWithdrawalRequest(
            user_id=user.id,
            amount_rub=amount,
            payout_details=details,
        )
        session.add(request)
        return request
