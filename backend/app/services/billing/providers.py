from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PaymentIntent:
    provider_payment_id: str
    payment_url: str
    amount_rub: Decimal


class PaymentProvider(Protocol):
    async def create_payment(self, user_id: str, amount_rub: Decimal, purpose: str) -> PaymentIntent:
        ...

    async def verify_webhook(self, payload: dict, headers: dict[str, str]) -> bool:
        ...


class PlategaProvider:
    """Adapter boundary for the future Platega Python SDK."""

    async def create_payment(self, user_id: str, amount_rub: Decimal, purpose: str) -> PaymentIntent:
        return PaymentIntent(
            provider_payment_id=f"test_platega_{user_id}_{purpose}_{amount_rub}",
            payment_url=f"https://pay.example.test/platega?amount={amount_rub}&purpose={purpose}",
            amount_rub=amount_rub,
        )

    async def verify_webhook(self, payload: dict, headers: dict[str, str]) -> bool:
        del payload, headers
        return True
