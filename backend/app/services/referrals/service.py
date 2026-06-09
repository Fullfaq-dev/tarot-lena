import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Referral, ReferralWithdrawalRequest, User
from app.database.session import AsyncSessionLocal
from app.services.billing.tokens import format_balance
from app.services.telegram_notify import notify_admins, notify_telegram_message

MIN_WITHDRAWAL_RUB = Decimal("3000")
DEFAULT_REWARD_PERCENT = 40
_RESERVED_WITHDRAWAL_STATUSES = ("pending", "approved")

_TRC20_WALLET_RE = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")


def is_valid_trc20_wallet(wallet: str) -> bool:
    return bool(_TRC20_WALLET_RE.match(wallet.strip()))


def next_friday() -> date:
    today = date.today()
    days_ahead = (4 - today.weekday()) % 7  # 4 = пятница
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def parse_withdrawal_amount(text: str) -> Decimal | None:
    cleaned = text.strip().replace(" ", "").replace("₽", "").replace(",", ".")
    try:
        amount = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    if amount <= 0:
        return None
    return amount.quantize(Decimal("0.01"))


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
            already_linked = await session.scalar(
                select(Referral).where(Referral.referred_user_id == referred.id)
            )
            referral = await self.attach_referrer(session, referrer, referred)
            if referral is None or already_linked is not None:
                return None
            await session.commit()

            referred_name = referred.first_name or referred.username or "новая подруга"
            notify_telegram_message(
                referrer.telegram_id,
                "🎉 По твоей ссылке присоединилась "
                f"{referred_name}!\n\n"
                "Как только она пополнит баланс или оформит подписку — "
                f"тебе начислится {DEFAULT_REWARD_PERCENT}% на реферальный баланс. 💰",
            )
            return referrer.first_name or referrer.username or "друг"

    async def accrue_reward(
        self, session: AsyncSession, referred_user_id: str, payment_amount: Decimal
    ) -> None:
        referral = await session.scalar(
            select(Referral).where(Referral.referred_user_id == referred_user_id)
        )
        if referral is None:
            return
        reward = payment_amount * Decimal(referral.reward_percent) / Decimal("100")
        referral.accrued_rub += reward
        await self._notify_referrer_payment(session, referral, referred_user_id, payment_amount, reward)

    async def _notify_referrer_payment(
        self,
        session: AsyncSession,
        referral: Referral,
        referred_user_id: str,
        payment_amount: Decimal,
        reward: Decimal,
    ) -> None:
        referrer = await session.scalar(select(User).where(User.id == referral.referrer_user_id))
        referred = await session.scalar(select(User).where(User.id == referred_user_id))
        if referrer is None:
            return
        referred_name = (referred.first_name or referred.username or "подруга") if referred else "подруга"
        notify_telegram_message(
            referrer.telegram_id,
            f"💰 {referred_name} пополнила баланс на {format_balance(payment_amount)}!\n"
            f"Тебе начислено {format_balance(reward)} ({referral.reward_percent}%) "
            "на реферальный баланс. ✨",
        )

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
                "🤝 Реферальная программа\n\n"
                f"💰 Доступно к выводу: {format_balance(stats['available'])}\n"
                f"📈 Всего заработано: {format_balance(stats['total_accrued'])}\n"
                f"👯 Приглашено друзей: {stats['referred_count']}\n\n"
                "Как это работает:\n"
                f"1️⃣ Отправь подруге свою ссылку\n"
                f"2️⃣ Она пополняет баланс или оформляет подписку\n"
                f"3️⃣ Тебе сразу падает {DEFAULT_REWARD_PERCENT}% от каждой её оплаты\n\n"
                f"💸 Вывод от {format_balance(MIN_WITHDRAWAL_RUB)} на USDT (сеть TRC-20). "
                "Выплаты — каждую пятницу.\n\n"
                f"🔗 Твоя ссылка:\n{link}"
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

    async def create_withdrawal_for_telegram(
        self,
        telegram_id: int,
        *,
        amount: Decimal,
        wallet: str,
    ) -> str:
        wallet = wallet.strip()
        if not is_valid_trc20_wallet(wallet):
            raise ValueError(
                "Это не похоже на USDT-кошелёк сети TRC-20.\n"
                "Адрес начинается с «T» и состоит из 34 символов, например:\n"
                "TXk3…\n\nПроверь и пришли ещё раз."
            )

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы я создала твой профиль."

            await self.request_withdrawal(
                session,
                user,
                amount,
                {"usdt_trc20": wallet, "network": "TRC-20"},
            )
            user.usdt_trc20_wallet = wallet
            await session.commit()

            user_label = user.first_name or user.username or str(telegram_id)
            await notify_admins(
                "💸 Новая заявка на вывод рефералки\n\n"
                f"👤 {user_label} (id {telegram_id})\n"
                f"💰 Сумма: {format_balance(amount)}\n"
                f"💼 USDT TRC-20: {wallet}\n\n"
                "Обработай в админ-дашборде → Рефералы."
            )

            payout_date = next_friday().strftime("%d.%m")
            short_wallet = f"{wallet[:8]}…{wallet[-6:]}"
            return (
                f"✅ Заявка на вывод {format_balance(amount)} принята!\n\n"
                f"💼 Кошелёк: {short_wallet} (USDT, TRC-20)\n"
                f"📅 Средства поступят в ближайшую пятницу — {payout_date}.\n\n"
                "Сумма уже зарезервирована и списана с реферального баланса."
            )

    async def get_saved_wallet(self, telegram_id: int) -> str | None:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            return user.usdt_trc20_wallet if user else None

    @staticmethod
    def _parse_referrer_telegram_id(start_code: str) -> int | None:
        code = (start_code or "").strip()
        if not code.lower().startswith("ref_"):
            return None
        raw_id = code[4:].strip()
        if not raw_id.isdigit():
            return None
        return int(raw_id)
