import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import BalanceTransaction, Payment, Subscription, UsageRecord, User, UserSettings
from app.database.session import AsyncSessionLocal
from app.core.config import get_settings
from app.bot.i18n import normalize_language, t
from app.bot.i18n_services import SPENDING_FEATURE_I18N
from app.services.billing.limits import (
    AI_MODEL_NAME,
    FREE_CHAT_MESSAGES_PER_MONTH,
    SPENDING_PAGE_SIZE,
    SUBSCRIPTION_PRICES_RUB,
    free_messages_left,
    is_unlimited_chat,
)
from app.services.billing.providers import PaymentIntent, PlategaProvider
from app.services.billing.tokens import (
    charge_rub,
    estimate_messages_tokens,
    estimate_tokens,
    format_balance,
    image_generation_charge_rub,
    image_generation_provider_cost_usd,
    vision_infographic_charge_rub,
    provider_cost_credits,
    provider_cost_usd,
    total_tokens,
)

logger = logging.getLogger(__name__)

_PAYMENT_DESCRIPTIONS = {
    "topup": "Пополнение баланса Arcana AI",
    "subscription_plus": "Подписка Plus Arcana AI",
    "subscription_premium": "Подписка Premium Arcana AI",
}


class BillingService:
    def __init__(self) -> None:
        self.provider = PlategaProvider()

    async def _user_lang(self, session: AsyncSession, user_id: str) -> str:
        settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user_id))
        return normalize_language(settings.ui_language if settings else "en")

    async def ensure_can_use_chat(
        self,
        session: AsyncSession,
        user: User,
        *,
        context_messages: list[dict] | None = None,
        answer_preview: str = "",
    ) -> tuple[bool, str, str]:
        """
        Возвращает (разрешено, сообщение_об_ошибке, режим).
        Режим: unlimited | free | balance | blocked
        """
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        tier = subscription.tier if subscription else "free"
        lang = await self._user_lang(session, user.id)

        if is_unlimited_chat(tier):
            return True, "", "unlimited"

        if user.free_messages_used_month < FREE_CHAT_MESSAGES_PER_MONTH:
            return True, "", "free"

        estimated_charge = self._estimate_charge(context_messages, answer_preview)
        if user.balance_rub >= estimated_charge:
            return True, "", "balance"

        if user.balance_rub > 0:
            return (
                False,
                t("billing_insufficient_balance", lang, balance=format_balance(user.balance_rub)),
                "blocked",
            )

        return (
            False,
            t(
                "billing_free_exhausted",
                lang,
                used=FREE_CHAT_MESSAGES_PER_MONTH,
                limit=FREE_CHAT_MESSAGES_PER_MONTH,
            ),
            "blocked",
        )

    def _estimate_charge(
        self, context_messages: list[dict] | None, answer_preview: str
    ) -> Decimal:
        input_tokens = estimate_messages_tokens(context_messages or [])
        output_tokens = max(estimate_tokens(answer_preview), 300)
        return charge_rub(input_tokens, output_tokens)

    async def reserve_chat_slot(self, session: AsyncSession, user: User, mode: str) -> str:
        """Списывает бесплатный слот только в режиме free."""
        if mode != "free":
            return mode
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        tier = subscription.tier if subscription else "free"
        if is_unlimited_chat(tier):
            return "unlimited"
        if user.free_messages_used_month < FREE_CHAT_MESSAGES_PER_MONTH:
            user.free_messages_used_month += 1
            await session.flush()
        return "free"

    async def ensure_can_use_vision(
        self,
        session: AsyncSession,
        user: User,
        *,
        with_infographic: bool,
        vision_mode: str | None = None,
        context_messages: list[dict] | None = None,
    ) -> tuple[bool, str, str]:
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        tier = subscription.tier if subscription else "free"
        lang = await self._user_lang(session, user.id)

        image_charge = vision_infographic_charge_rub(vision_mode) if with_infographic else Decimal("0")

        if is_unlimited_chat(tier):
            if not with_infographic or user.balance_rub >= image_charge:
                return True, "", "unlimited"
            return (
                False,
                t("billing_infographic_needed", lang, amount=format_balance(image_charge)),
                "blocked",
            )
        if with_infographic and user.balance_rub < image_charge:
            return (
                False,
                t("billing_infographic_needed", lang, amount=format_balance(image_charge)),
                "blocked",
            )

        if user.free_messages_used_month < FREE_CHAT_MESSAGES_PER_MONTH:
            return True, "", "free"

        estimated_charge = self._estimate_charge(context_messages, "")
        if user.balance_rub >= estimated_charge:
            return True, "", "balance"

        if user.balance_rub > 0:
            return (
                False,
                t("billing_insufficient_photo", lang, balance=format_balance(user.balance_rub)),
                "blocked",
            )

        return (
            False,
            t(
                "billing_free_exhausted",
                lang,
                used=FREE_CHAT_MESSAGES_PER_MONTH,
                limit=FREE_CHAT_MESSAGES_PER_MONTH,
            ),
            "blocked",
        )

    async def get_balance_label(self, telegram_id: int) -> str:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return format_balance(Decimal("0"))
            return format_balance(user.balance_rub)

    async def record_chat_usage(
        self,
        session: AsyncSession,
        user: User,
        question: str,
        answer: str,
        *,
        feature: str = "chat",
        context_messages: list[dict] | None = None,
        api_usage: dict[str, int] | None = None,
        billing_mode: str = "free",
        extra_meta: dict | None = None,
    ) -> dict:
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        tier = subscription.tier if subscription else "free"

        question_tokens = estimate_tokens(question)
        answer_tokens = estimate_tokens(answer)

        if api_usage and api_usage.get("input_tokens"):
            input_tokens = api_usage["input_tokens"]
            output_tokens = api_usage.get("output_tokens") or answer_tokens
            cost_source = "kie_api"
        else:
            input_tokens = estimate_messages_tokens(context_messages) if context_messages else question_tokens
            output_tokens = answer_tokens
            cost_source = "estimated"

        cost_credits = provider_cost_credits(input_tokens, output_tokens)
        cost_usd = provider_cost_usd(input_tokens, output_tokens)
        charged = Decimal("0")

        if not is_unlimited_chat(tier) and billing_mode == "balance":
            charged = charge_rub(input_tokens, output_tokens)
            if user.balance_rub >= charged:
                user.balance_rub -= charged
                session.add(
                    BalanceTransaction(user_id=user.id, amount_rub=-charged, reason="chat_usage")
                )
            else:
                charged = Decimal("0")

        usage = UsageRecord(
            user_id=user.id,
            feature=feature,
            provider="kie",
            model=AI_MODEL_NAME,
            input_units=input_tokens,
            output_units=output_tokens,
            provider_cost_usd=cost_usd,
            charged_rub=charged,
            meta={
                "question_tokens": question_tokens,
                "answer_tokens": answer_tokens,
                "question_preview": question[:200],
                "billing_mode": billing_mode,
                "cost_source": cost_source,
                "billing_credit_usd": str(get_settings().billing_credit_usd),
                "charge_markup": str(get_settings().charge_markup),
                "total_tokens": total_tokens(input_tokens, output_tokens),
                "kie_credits": str(cost_credits),
                **(extra_meta or {}),
            },
        )
        session.add(usage)
        await session.flush()
        return {
            "usage_record_id": usage.id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "question_tokens": question_tokens,
            "answer_tokens": answer_tokens,
            "provider_cost_usd": cost_usd,
            "kie_credits": cost_credits,
            "charged_rub": charged,
            "model": AI_MODEL_NAME,
            "billing_mode": billing_mode,
            "balance_after": user.balance_rub,
        }

    async def record_vision_usage(
        self,
        session: AsyncSession,
        user: User,
        question: str,
        answer: str,
        *,
        feature: str,
        context_messages: list[dict] | None = None,
        api_usage: dict[str, int] | None = None,
        billing_mode: str = "free",
        with_infographic: bool = False,
        vision_mode: str | None = None,
        extra_meta: dict | None = None,
    ) -> dict:
        usage = await self.record_chat_usage(
            session,
            user,
            question,
            answer,
            feature=feature,
            context_messages=context_messages,
            api_usage=api_usage,
            billing_mode=billing_mode,
            extra_meta=extra_meta,
        )

        if not with_infographic:
            return usage

        image_cost_usd = image_generation_provider_cost_usd()
        image_charge = vision_infographic_charge_rub(vision_mode)
        chat_charged = Decimal(str(usage["charged_rub"]))
        chat_cost_usd = Decimal(str(usage["provider_cost_usd"]))
        image_charged = Decimal("0")

        if user.balance_rub >= image_charge:
            user.balance_rub -= image_charge
            session.add(
                BalanceTransaction(user_id=user.id, amount_rub=-image_charge, reason="vision_infographic")
            )
            image_charged = image_charge

        total_charged = chat_charged + image_charged
        total_cost_usd = chat_cost_usd + image_cost_usd

        record = await session.get(UsageRecord, usage["usage_record_id"])
        if record is not None:
            record.charged_rub = total_charged
            record.provider_cost_usd = total_cost_usd
            record.meta = {
                **(record.meta or {}),
                "with_infographic": True,
                "image_model": "gpt-image-2-image-to-image",
                "image_provider_cost_usd": str(image_cost_usd),
                "image_charged_rub": str(image_charged),
                "chat_charged_rub": str(chat_charged),
                "chat_provider_cost_usd": str(chat_cost_usd),
            }

        usage["image_charged_rub"] = image_charged
        usage["charged_rub"] = total_charged
        usage["provider_cost_usd"] = total_cost_usd
        usage["balance_after"] = user.balance_rub
        usage["with_infographic"] = True
        await session.flush()
        return usage

    async def panel_text(self, telegram_id: int) -> str:
        from app.services.referrals.service import MIN_WITHDRAWAL_RUB, ReferralService

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            lang = await self._user_lang(session, user.id) if user else "en"
            if user is None:
                return t("error_need_start", lang)

            subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
            tier = subscription.tier if subscription else "free"
            free_left = free_messages_left(user.free_messages_used_month)
            readings_left = max(0, 3 - user.free_readings_used_month)

            tier_label = {
                "free": t("tier_free", lang),
                "plus": "Plus",
                "premium": "Premium",
            }.get(tier, tier)

            ref_stats = await ReferralService().get_stats(session, user)
            return t(
                "billing_panel",
                lang,
                tier=tier_label,
                balance=format_balance(user.balance_rub),
                ref_balance=format_balance(ref_stats["available"]),
                free_left=free_left,
                free_limit=FREE_CHAT_MESSAGES_PER_MONTH,
                readings_left=readings_left,
                plus_price=format_balance(SUBSCRIPTION_PRICES_RUB["plus"]),
                premium_price=format_balance(SUBSCRIPTION_PRICES_RUB["premium"]),
                min_withdraw=format_balance(MIN_WITHDRAWAL_RUB),
            )

    async def spending_history_page(
        self, telegram_id: int, page: int = 0
    ) -> tuple[str, int, int]:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            lang = await self._user_lang(session, user.id) if user else "en"
            if user is None:
                return t("error_need_start", lang), 0, 0

            total = await session.scalar(
                select(func.count())
                .select_from(UsageRecord)
                .where(UsageRecord.user_id == user.id, UsageRecord.charged_rub > 0)
            )
            total = int(total or 0)
            if total == 0:
                return t("billing_spending_empty", lang), 0, 0

            total_pages = max(1, (total + SPENDING_PAGE_SIZE - 1) // SPENDING_PAGE_SIZE)
            page = max(0, min(page, total_pages - 1))
            offset = page * SPENDING_PAGE_SIZE

            records = await session.scalars(
                select(UsageRecord)
                .where(UsageRecord.user_id == user.id, UsageRecord.charged_rub > 0)
                .order_by(UsageRecord.created_at.desc())
                .offset(offset)
                .limit(SPENDING_PAGE_SIZE)
            )

            lines = [
                t("billing_spending_title", lang),
                t("history_page", lang, page=page + 1, total=total_pages) + "\n",
            ]
            for record in records:
                feature_key = SPENDING_FEATURE_I18N.get(record.feature)
                label = t(feature_key, lang) if feature_key else record.feature
                when = record.created_at.strftime("%d.%m %H:%M")
                lines.append(
                    t(
                        "billing_spending_line",
                        lang,
                        when=when,
                        label=label,
                        amount=format_balance(record.charged_rub),
                    )
                )
            return "\n".join(lines), page, total_pages

    async def create_topup_for_telegram(self, telegram_id: int, amount: Decimal) -> str:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            lang = await self._user_lang(session, user.id) if user else "en"
            if user is None:
                return t("error_need_start", lang)
            intent = await self.create_topup(session, user, amount)
            return t("billing_topup_link", lang, amount=amount, url=intent.payment_url)

    async def create_subscription_for_telegram(self, telegram_id: int, tier: str) -> str:
        amount = SUBSCRIPTION_PRICES_RUB.get(tier)
        if amount is None:
            return t("billing_unknown_tier", "en")

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            lang = await self._user_lang(session, user.id) if user else "en"
            if user is None:
                return t("error_need_start", lang)

            intent = await self._initiate_platega_payment(
                session,
                user,
                amount,
                f"subscription_{tier}",
            )
            label = "Plus" if tier == "plus" else "Premium"
            return t("billing_sub_link", lang, label=label, amount=amount, url=intent.payment_url)

    async def admin_topup_balance(
        self,
        session: AsyncSession,
        user: User,
        amount: Decimal,
        *,
        comment: str = "",
    ) -> dict:
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть больше нуля")

        user.balance_rub += amount
        reason = "admin_topup"
        if comment.strip():
            reason = f"admin_topup: {comment.strip()[:120]}"
        session.add(
            BalanceTransaction(user_id=user.id, amount_rub=amount, reason=reason)
        )
        await session.flush()
        return {
            "amount_rub": amount,
            "balance_rub": user.balance_rub,
        }

    async def create_topup(self, session: AsyncSession, user: User, amount: Decimal) -> PaymentIntent:
        return await self._initiate_platega_payment(session, user, amount, "topup")

    async def _initiate_platega_payment(
        self,
        session: AsyncSession,
        user: User,
        amount: Decimal,
        purpose: str,
    ) -> PaymentIntent:
        payment = Payment(
            user_id=user.id,
            provider="platega",
            purpose=purpose,
            amount_rub=amount,
            status="pending",
        )
        session.add(payment)
        await session.flush()

        description = _PAYMENT_DESCRIPTIONS.get(purpose, f"Оплата Arcana AI ({purpose})")
        intent = await self.provider.create_payment(
            payment_id=str(payment.id),
            amount_rub=amount,
            purpose=purpose,
            description=description,
        )
        payment.provider_payment_id = intent.provider_payment_id
        payment.payload = {"payment_url": intent.payment_url}
        await session.commit()
        return intent

    async def process_platega_callback(
        self,
        session: AsyncSession,
        *,
        transaction_id: str,
        payment_id: str | None,
        status: str,
    ) -> None:
        payment = None
        if payment_id:
            payment = await session.scalar(select(Payment).where(Payment.id == payment_id))
        if payment is None and transaction_id:
            payment = await session.scalar(
                select(Payment).where(Payment.provider_payment_id == transaction_id)
            )
        if payment is None:
            logger.warning(
                "Platega callback for unknown payment: tx=%s payment_id=%s",
                transaction_id,
                payment_id,
            )
            return

        if payment.status != "pending":
            logger.info("Platega callback ignored for payment %s with status %s", payment.id, payment.status)
            return

        payload = dict(payment.payload or {})
        payload["platega_status"] = status
        payload["platega_transaction_id"] = transaction_id
        payment.payload = payload

        if status == "CONFIRMED":
            await self.complete_payment(session, payment)
        elif status in {"CANCELED", "CHARGEBACKED"}:
            await self.reject_payment(
                session,
                payment,
                admin_comment=f"Platega status: {status}",
            )

    async def complete_payment(
        self,
        session: AsyncSession,
        payment: Payment,
        *,
        admin_comment: str = "",
    ) -> dict:
        if payment.status != "pending":
            raise ValueError("Можно провести только ожидающий платёж")

        user = await session.scalar(select(User).where(User.id == payment.user_id))
        if user is None:
            raise ValueError("Пользователь не найден")

        if payment.purpose == "topup":
            existing = await session.scalar(
                select(BalanceTransaction).where(BalanceTransaction.payment_id == payment.id)
            )
            if existing is None:
                user.balance_rub += payment.amount_rub
                session.add(
                    BalanceTransaction(
                        user_id=user.id,
                        amount_rub=payment.amount_rub,
                        reason="payment_topup",
                        payment_id=payment.id,
                    )
                )
        elif payment.purpose.startswith("subscription_"):
            tier = payment.purpose.removeprefix("subscription_")
            if tier not in SUBSCRIPTION_PRICES_RUB:
                raise ValueError(f"Неизвестный тариф: {tier}")

            now = datetime.now(timezone.utc)
            subscription = await session.scalar(
                select(Subscription).where(Subscription.user_id == user.id)
            )
            if subscription is None:
                subscription = Subscription(user_id=user.id)
                session.add(subscription)
                await session.flush()

            subscription.tier = tier
            subscription.status = "active"
            subscription.started_at = now
            subscription.expires_at = now + timedelta(days=30)
            subscription.provider = payment.provider
            subscription.provider_subscription_id = payment.provider_payment_id
        else:
            raise ValueError(f"Неизвестное назначение платежа: {payment.purpose}")

        from app.services.referrals.service import ReferralService

        await ReferralService().accrue_reward(session, user.id, payment.amount_rub)

        payment.status = "completed"
        if admin_comment.strip():
            payload = dict(payment.payload or {})
            payload["admin_comment"] = admin_comment.strip()[:200]
            payment.payload = payload

        await session.flush()
        return {
            "payment_id": payment.id,
            "status": payment.status,
            "purpose": payment.purpose,
            "amount_rub": payment.amount_rub,
            "balance_rub": user.balance_rub,
        }

    async def reject_payment(
        self,
        session: AsyncSession,
        payment: Payment,
        *,
        admin_comment: str = "",
    ) -> dict:
        if payment.status != "pending":
            raise ValueError("Можно отклонить только ожидающий платёж")

        payment.status = "rejected"
        if admin_comment.strip():
            payload = dict(payment.payload or {})
            payload["admin_comment"] = admin_comment.strip()[:200]
            payment.payload = payload

        await session.flush()
        return {"payment_id": payment.id, "status": payment.status}

    async def delete_payment(self, session: AsyncSession, payment: Payment) -> None:
        if payment.status == "completed":
            raise ValueError("Нельзя удалить проведённый платёж")
        await session.delete(payment)
