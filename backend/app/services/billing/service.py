from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import BalanceTransaction, Payment, Subscription, UsageRecord, User
from app.database.session import AsyncSessionLocal
from app.core.config import get_settings
from app.services.billing.limits import (
    AI_MODEL_NAME,
    FREE_CHAT_MESSAGES_PER_MONTH,
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
    provider_cost_credits,
    provider_cost_usd,
    total_tokens,
)


class BillingService:
    def __init__(self) -> None:
        self.provider = PlategaProvider()

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
                f"На балансе {format_balance(user.balance_rub)} — недостаточно для ответа. "
                "Пополни баланс — нажми «Баланс».",
                "blocked",
            )

        return (
            False,
            f"Бесплатные сообщения закончились ({FREE_CHAT_MESSAGES_PER_MONTH}/{FREE_CHAT_MESSAGES_PER_MONTH}). "
            "Пополни баланс или подключи Plus/Premium — нажми «Баланс».",
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
        context_messages: list[dict] | None = None,
    ) -> tuple[bool, str, str]:
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        tier = subscription.tier if subscription else "free"

        if is_unlimited_chat(tier):
            if not with_infographic or user.balance_rub >= image_generation_charge_rub():
                return True, "", "unlimited"
            return (
                False,
                f"Для инфографики нужно {format_balance(image_generation_charge_rub())} на балансе. "
                "Пополни баланс — нажми «Баланс».",
                "blocked",
            )

        image_charge = image_generation_charge_rub() if with_infographic else Decimal("0")
        if with_infographic and user.balance_rub < image_charge:
            return (
                False,
                f"Для инфографики нужно {format_balance(image_charge)} на балансе. "
                "Пополни баланс — нажми «Баланс».",
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
                f"На балансе {format_balance(user.balance_rub)} — недостаточно для анализа фото. "
                "Пополни баланс — нажми «Баланс».",
                "blocked",
            )

        return (
            False,
            f"Бесплатные сообщения закончились ({FREE_CHAT_MESSAGES_PER_MONTH}/{FREE_CHAT_MESSAGES_PER_MONTH}). "
            "Пополни баланс — нажми «Баланс».",
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
        )

        if not with_infographic:
            return usage

        image_cost_usd = image_generation_provider_cost_usd()
        image_charge = image_generation_charge_rub()
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        tier = subscription.tier if subscription else "free"

        if user.balance_rub >= image_charge:
            user.balance_rub -= image_charge
            session.add(
                BalanceTransaction(user_id=user.id, amount_rub=-image_charge, reason="vision_infographic")
            )
            usage["image_charged_rub"] = image_charge
            usage["charged_rub"] = Decimal(str(usage["charged_rub"])) + image_charge
        else:
            usage["image_charged_rub"] = Decimal("0")

        usage["provider_cost_usd"] = Decimal(str(usage["provider_cost_usd"])) + image_cost_usd
        usage["balance_after"] = user.balance_rub
        usage["with_infographic"] = True
        await session.flush()
        return usage

    async def panel_text(self, telegram_id: int) -> str:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы я создала твой профиль."

            subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
            tier = subscription.tier if subscription else "free"
            free_left = free_messages_left(user.free_messages_used_month)
            readings_left = max(0, 3 - user.free_readings_used_month)

            tier_label = {"free": "Бесплатный", "plus": "Plus", "premium": "Premium"}.get(
                tier, tier
            )
            return (
                "Подписка и баланс\n\n"
                f"Тариф: {tier_label}\n"
                f"Баланс: {format_balance(user.balance_rub)}\n"
                f"Бесплатных сообщений: {free_left} из {FREE_CHAT_MESSAGES_PER_MONTH}\n"
                f"Бесплатных раскладов: {readings_left} из 3\n\n"
                "Plus — безлимитный чат.\n"
                "Premium — безлимитный чат и голосовые ответы."
            )

    async def create_topup_for_telegram(self, telegram_id: int, amount: Decimal) -> str:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы я создала твой профиль."
            intent = await self.create_topup(session, user, amount)
            return (
                f"Ссылка на оплату {amount} ₽:\n{intent.payment_url}\n\n"
                "После успешной оплаты баланс обновится автоматически."
            )

    async def create_subscription_for_telegram(self, telegram_id: int, tier: str) -> str:
        amount = SUBSCRIPTION_PRICES_RUB.get(tier)
        if amount is None:
            return "Неизвестный тариф."

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return "Сначала нажми /start, чтобы я создала твой профиль."

            intent = await self.provider.create_payment(user.id, amount, f"subscription_{tier}")
            session.add(
                Payment(
                    user_id=user.id,
                    provider="platega",
                    provider_payment_id=intent.provider_payment_id,
                    purpose=f"subscription_{tier}",
                    amount_rub=amount,
                )
            )
            await session.commit()
            label = "Plus" if tier == "plus" else "Premium"
            return (
                f"Подписка {label} — {amount} ₽/мес.\n"
                f"Ссылка на оплату:\n{intent.payment_url}\n\n"
                "После оплаты тариф активируется автоматически."
            )

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
        intent = await self.provider.create_payment(user.id, amount, "topup")
        session.add(
            Payment(
                user_id=user.id,
                provider="platega",
                provider_payment_id=intent.provider_payment_id,
                purpose="topup",
                amount_rub=amount,
            )
        )
        await session.commit()
        return intent

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
