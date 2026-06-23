import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.i18n import normalize_language, t
from app.database.models import Payment, Referral, ReferralWithdrawalRequest, User, UserSettings
from app.database.session import AsyncSessionLocal
from app.services.billing.tokens import format_balance
from app.services.telegram_notify import notify_admins, notify_telegram_message

MIN_WITHDRAWAL_RUB = Decimal("3000")
DEFAULT_REWARD_PERCENT = 40
REFERRAL_LIST_PAGE_SIZE = 8
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


def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class ReferredUserRow:
    name: str
    joined_at: datetime
    earned_rub: Decimal


class ReferralService:
    async def _user_lang(self, session: AsyncSession, user: User) -> str:
        settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
        return normalize_language(settings.ui_language if settings else "en")

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

            lang = await self._user_lang(session, referrer)
            referred_name = (
                referred.first_name or referred.username or t("referral_new_user", lang)
            )
            notify_telegram_message(
                referrer.telegram_id,
                t(
                    "referral_joined_notify",
                    lang,
                    name=referred_name,
                    percent=DEFAULT_REWARD_PERCENT,
                ),
            )
            return referrer.first_name or referrer.username or t("referral_friend", lang)

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
        lang = await self._user_lang(session, referrer)
        referred_name = (
            (referred.first_name or referred.username or t("referral_friend", lang))
            if referred
            else t("referral_friend", lang)
        )
        notify_telegram_message(
            referrer.telegram_id,
            t(
                "referral_payment_notify",
                lang,
                name=referred_name,
                amount=format_balance(payment_amount),
                reward=format_balance(reward),
                percent=referral.reward_percent,
            ),
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

    async def get_daily_stats(self, session: AsyncSession, user: User) -> dict[str, Decimal | int]:
        today_start = _today_start_utc()
        joined_today = await session.scalar(
            select(func.count())
            .select_from(Referral)
            .where(
                Referral.referrer_user_id == user.id,
                Referral.created_at >= today_start,
            )
        )
        earned_today = await session.scalar(
            select(
                func.coalesce(
                    func.sum(Payment.amount_rub * Referral.reward_percent / Decimal("100")),
                    0,
                )
            )
            .select_from(Payment)
            .join(Referral, Referral.referred_user_id == Payment.user_id)
            .where(
                Referral.referrer_user_id == user.id,
                Payment.status == "completed",
                Payment.updated_at >= today_start,
            )
        )
        return {
            "joined_today": int(joined_today or 0),
            "earned_today": Decimal(earned_today or 0),
        }

    async def stats_panel_text(self, telegram_id: int) -> str:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", "en")
            lang = await self._user_lang(session, user)
            totals = await self.get_stats(session, user)
            daily = await self.get_daily_stats(session, user)
            return t(
                "referral_stats_panel",
                lang,
                joined_today=daily["joined_today"],
                earned_today=format_balance(daily["earned_today"]),
                count=totals["referred_count"],
                total=format_balance(totals["total_accrued"]),
                available=format_balance(totals["available"]),
            )

    async def referred_users_page(
        self,
        telegram_id: int,
        page: int,
        *,
        sort_newest_first: bool = True,
    ) -> tuple[str, list[ReferredUserRow], int, int]:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", "en"), [], 0, 1

            lang = await self._user_lang(session, user)
            total_count = await session.scalar(
                select(func.count())
                .select_from(Referral)
                .where(Referral.referrer_user_id == user.id)
            )
            total_count = int(total_count or 0)
            total_pages = max(1, (total_count + REFERRAL_LIST_PAGE_SIZE - 1) // REFERRAL_LIST_PAGE_SIZE)
            page = max(0, min(page, total_pages - 1))

            order = Referral.created_at.desc() if sort_newest_first else Referral.created_at.asc()
            offset = page * REFERRAL_LIST_PAGE_SIZE
            rows = await session.execute(
                select(Referral, User)
                .join(User, User.id == Referral.referred_user_id)
                .where(Referral.referrer_user_id == user.id)
                .order_by(order)
                .offset(offset)
                .limit(REFERRAL_LIST_PAGE_SIZE)
            )

            items: list[ReferredUserRow] = []
            for referral, referred in rows.all():
                name = referred.first_name or referred.username or t("referral_friend", lang)
                items.append(
                    ReferredUserRow(
                        name=name,
                        joined_at=referral.created_at,
                        earned_rub=referral.accrued_rub,
                    )
                )

            if total_count == 0:
                return t("referral_list_empty", lang), [], page, total_pages

            sort_label = t("referral_sort_newest", lang) if sort_newest_first else t("referral_sort_oldest", lang)
            lines = [
                t("referral_list_title", lang),
                t("history_page", lang, page=page + 1, total=total_pages),
                t("referral_list_sort", lang, sort=sort_label),
                "",
            ]
            start_index = offset + 1
            for index, item in enumerate(items, start=start_index):
                joined = item.joined_at.strftime("%d.%m.%Y")
                lines.append(
                    t(
                        "referral_list_line",
                        lang,
                        index=index,
                        name=item.name,
                        date=joined,
                        earned=format_balance(item.earned_rub),
                    )
                )
            return "\n".join(lines), items, page, total_pages

    def build_referral_link(self, bot_username: str, telegram_id: int) -> str:
        username = bot_username.lstrip("@")
        return f"https://t.me/{username}?start=ref_{telegram_id}"

    async def panel_text(self, telegram_id: int, *, bot_username: str | None = None) -> str:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", "en")

            lang = await self._user_lang(session, user)
            stats = await self.get_stats(session, user)
            link = (
                self.build_referral_link(bot_username, telegram_id)
                if bot_username
                else f"ref_{telegram_id}"
            )

            return t(
                "referral_panel",
                lang,
                available=format_balance(stats["available"]),
                total=format_balance(stats["total_accrued"]),
                count=stats["referred_count"],
                percent=DEFAULT_REWARD_PERCENT,
                min_withdraw=format_balance(MIN_WITHDRAWAL_RUB),
                link=link,
            )

    async def request_withdrawal(
        self, session: AsyncSession, user: User, amount: Decimal, details: dict
    ) -> ReferralWithdrawalRequest:
        lang = await self._user_lang(session, user)
        if amount < MIN_WITHDRAWAL_RUB:
            raise ValueError(
                t("referral_withdraw_min_error", lang, min=format_balance(MIN_WITHDRAWAL_RUB))
            )
        stats = await self.get_stats(session, user)
        available = stats["available"]
        if amount > available:
            raise ValueError(
                t(
                    "referral_withdraw_insufficient_error",
                    lang,
                    available=format_balance(available),
                )
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
            raise ValueError(t("referral_withdraw_pending_exists", lang))

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
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", "en")
            lang = await self._user_lang(session, user)

        if not is_valid_trc20_wallet(wallet):
            raise ValueError(t("referral_withdraw_invalid_wallet", lang))

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return t("error_need_start", lang)

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
            return t(
                "referral_withdraw_accepted",
                lang,
                amount=format_balance(amount),
                wallet=f"{short_wallet}",
                payout_date=payout_date,
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
