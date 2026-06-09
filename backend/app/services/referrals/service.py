from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Referral, ReferralWithdrawalRequest, User
from app.database.session import AsyncSessionLocal
from app.services.billing.tokens import format_balance

MIN_WITHDRAWAL_RUB = Decimal("3000")
DEFAULT_REWARD_PERCENT = 40
_RESERVED_WITHDRAWAL_STATUSES = ("pending", "approved")


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
        referral = Referral(
            referrer_user_id=referrer.id,
            referred_user_id=referred.id,
            reward_percent=DEFAULT_REWARD_PERCENT,
        )
        session.add(referral)
        return referral

    async def attach_from_start_code(self, referred_telegram_id: int, start_code: str) -> str | None:
        referrer_telegram_id = self._parse_referrer_telegram_id(start_code)
        if referrer_telegram_id is None:
            return None
        if referrer_telegram_id == referred_telegram_id:
            return None

        async with AsyncSessionLocal() as session:
            referrer = await session.scalar(
                select(User).where(User.telegram_id == referrer_telegram_id)
            )
            referred = await session.scalar(
                select(User).where(User.telegram_id == referred_telegram_id)
            )
            if referrer is None or referred is None:
                return None
            referral = await self.attach_referrer(session, referrer, referred)
            if referral is None:
                return None
            await session.commit()
            return referrer.first_name or referrer.username or "друг"

    async def accrue_reward(
        self, session: AsyncSession, referred_user_id: str, payment_amount: Decimal
    ) -> None:
        referral = await session.scalar(
            select(Referral).where(Referral.referred_user_id == referred_user_id)
        )
        if referral is None:
            return
        referral.accrued_rub += payment_amount * Decimal(referral.reward_percent) / Decimal("100")

    async def get_stats(self, session: AsyncSession, user: User) -> dict[str, Decimal | int]:
        total_accrued = await session.scalar(
            select(func.coalesce(func.sum(Referral.accrued_rub), 0)).where(
                Referral.referrer_user_id == user.id
            )
        )
        reserved = await session.scalar(
            select(func.coalesce(func.sum(ReferralWithdrawalRequest.amount_rub), 0)).where(
                ReferralWithdrawalRequest.user_id == user.id,
                ReferralWithdrawalRequest.status.in_(_RESERVED_WITHDRAWAL_STATUSES),
            )
        )
        referred_count = await session.scalar(
            select(func.count()).select_from(Referral).where(Referral.referrer_user_id == user.id)
        )
        total_accrued = Decimal(total_accrued or 0)
        reserved = Decimal(reserved or 0)
        available = max(Decimal("0"), total_accrued - reserved)
        return {
            "total_accrued": total_accrued,
            "reserved": reserved,
            "available": available,
            "referred_count": int(referred_count or 0),
        }

    def build_referral_link(self, bot_username: str, telegram_id: int) -> str:
        username = bot_username.lstrip("@")
        return f"https://t.me/{username}?start=ref_{telegram_id}"

    async def panel_text(self, telegram_id: int, *, bot_username: str | None = None) -> str:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы я создала твой профиль."

            stats = await self.get_stats(session, user)
            link = (
                self.build_referral_link(bot_username, telegram_id)
                if bot_username
                else f"ref_{telegram_id}"
            )

            return (
                "Реферальная программа\n\n"
                f"Твой баланс: {format_balance(stats['available'])}\n"
                f"Всего начислено: {format_balance(stats['total_accrued'])}\n"
                f"Приглашено друзей: {stats['referred_count']}\n"
                f"Процент с оплат: {DEFAULT_REWARD_PERCENT}%\n\n"
                "Как это работает:\n"
                "• отправь ссылку другу\n"
                "• когда он пополнит баланс или оформит подписку — тебе начисляется 40% от суммы\n"
                f"• вывод от {format_balance(MIN_WITHDRAWAL_RUB)} — заявка уходит админу\n\n"
                f"Твоя ссылка:\n{link}"
            )

    async def request_withdrawal(
        self, session: AsyncSession, user: User, amount: Decimal, details: dict
    ) -> ReferralWithdrawalRequest:
        if amount < MIN_WITHDRAWAL_RUB:
            raise ValueError(f"Минимальная сумма вывода — {format_balance(MIN_WITHDRAWAL_RUB)}.")
        stats = await self.get_stats(session, user)
        available = stats["available"]
        if amount > available:
            raise ValueError(
                f"Недостаточно средств. Доступно: {format_balance(available)}."
            )
        pending = await session.scalar(
            select(func.count())
            .select_from(ReferralWithdrawalRequest)
            .where(
                ReferralWithdrawalRequest.user_id == user.id,
                ReferralWithdrawalRequest.status == "pending",
            )
        )
        if pending:
            raise ValueError("У тебя уже есть заявка на вывод в обработке.")

        request = ReferralWithdrawalRequest(
            user_id=user.id,
            amount_rub=amount,
            payout_details=details,
        )
        session.add(request)
        return request

    async def request_withdrawal_for_telegram(
        self,
        telegram_id: int,
        *,
        payout_details_text: str,
    ) -> str:
        details = {"text": payout_details_text.strip()}
        if not details["text"]:
            raise ValueError("Напиши реквизиты для вывода.")

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы я создала твой профиль."

            stats = await self.get_stats(session, user)
            amount = stats["available"]
            await self.request_withdrawal(session, user, amount, details)
            await session.commit()
            return (
                f"Заявка на вывод {format_balance(amount)} принята.\n"
                "Админ обработает её вручную — обычно в течение 1–3 рабочих дней."
            )

    @staticmethod
    def _parse_referrer_telegram_id(start_code: str) -> int | None:
        code = (start_code or "").strip()
        if not code.lower().startswith("ref_"):
            return None
        raw_id = code[4:].strip()
        if not raw_id.isdigit():
            return None
        return int(raw_id)
