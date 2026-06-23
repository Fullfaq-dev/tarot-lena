import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.core.config import get_settings
from app.services.billing.platega_client import (
    PlategaNotConfiguredError,
    create_platega_payment,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaymentIntent:
    provider_payment_id: str
    payment_url: str
    amount_rub: Decimal


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


class PlategaProvider:
    """Platega.io payment provider via official Python SDK."""

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
