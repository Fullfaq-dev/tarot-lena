import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.core.config import get_settings
from app.services.billing.platega_client import (
    PlategaNotConfiguredError,
    create_platega_payment,
)
from app.services.billing.robokassa_client import (
    RobokassaNotConfiguredError,
    build_payment_url,
    next_invoice_id,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaymentIntent:
    provider_payment_id: str
    payment_url: str
    amount_rub: Decimal


@dataclass(frozen=True)
class PaymentFlowResult:
    amount_rub: str
    payment_url: str | None = None
    completed: bool = False
    user_text: str | None = None
    product_text: str | None = None
    product_id: str | None = None
    tarot_question: str | None = None
    tarot_cards: tuple[dict, ...] | None = None


class PaymentProvider(Protocol):
    async def create_payment(
        self,
        *,
        payment_id: str,
        amount_rub: Decimal,
        purpose: str,
        description: str,
    ) -> PaymentIntent:
        ...

    async def verify_webhook(self, payload: dict, headers: dict[str, str]) -> bool:
        ...


class RobokassaProvider:
    """Robokassa payment form (MD5 SignatureValue)."""

    async def create_payment(
        self,
        *,
        payment_id: str,
        amount_rub: Decimal,
        purpose: str,
        description: str,
    ) -> PaymentIntent:
        del purpose
        settings = get_settings()
        try:
            inv_id = await next_invoice_id()
            url = build_payment_url(
                payment_id=payment_id,
                inv_id=inv_id,
                amount_rub=amount_rub,
                description=description,
            )
            return PaymentIntent(
                provider_payment_id=str(inv_id),
                payment_url=url,
                amount_rub=amount_rub,
            )
        except RobokassaNotConfiguredError:
            if settings.app_env == "local":
                logger.warning("Robokassa not configured — using local test payment URL")
                return PaymentIntent(
                    provider_payment_id=f"test_rk_{payment_id}",
                    payment_url=f"https://pay.example.test/robokassa?amount={amount_rub}",
                    amount_rub=amount_rub,
                )
            raise

    async def verify_webhook(self, payload: dict, headers: dict[str, str]) -> bool:
        del payload, headers
        return True


class PlategaProvider:
    """Platega.io payment provider via official Python SDK (legacy)."""

    async def create_payment(
        self,
        *,
        payment_id: str,
        amount_rub: Decimal,
        purpose: str,
        description: str,
    ) -> PaymentIntent:
        settings = get_settings()
        try:
            result = await create_platega_payment(
                payment_id=payment_id,
                amount_rub=amount_rub,
                description=description,
            )
            return PaymentIntent(
                provider_payment_id=result["transaction_id"],
                payment_url=result["redirect"],
                amount_rub=amount_rub,
            )
        except PlategaNotConfiguredError:
            if settings.app_env == "local":
                logger.warning("Platega not configured — using local test payment URL")
                return PaymentIntent(
                    provider_payment_id=f"test_platega_{payment_id}",
                    payment_url=f"https://pay.example.test/platega?amount={amount_rub}&purpose={purpose}",
                    amount_rub=amount_rub,
                )
            raise

    async def verify_webhook(self, payload: dict, headers: dict[str, str]) -> bool:
        del payload, headers
        return True
