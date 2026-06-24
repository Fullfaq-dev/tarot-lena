from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Any

from platega import Platega, PlategaAPIError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PlategaNotConfiguredError(RuntimeError):
    pass


def get_platega_client() -> Platega | None:
    settings = get_settings()
    if not settings.platega_merchant_id or not settings.platega_api_key:
        return None
    return Platega(settings.platega_merchant_id, settings.platega_api_key)


def require_platega_client() -> Platega:
    client = get_platega_client()
    if client is None:
        raise PlategaNotConfiguredError("Platega credentials are not configured")
    return client


async def fetch_balances() -> tuple[list[dict[str, Any]], str | None]:
    client = get_platega_client()
    if client is None:
        return [], "Platega не настроена (PLATEGA_MERCHANT_ID / PLATEGA_API_KEY)"
    try:
        raw = await asyncio.to_thread(client.get_balances)
    except PlategaAPIError as exc:
        logger.warning("Platega balances request failed: %s", exc)
        return [], str(exc)
    balances: list[dict[str, Any]] = []
    for item in raw:
        balances.append(
            {
                "amount": float(item.get("amount", 0)),
                "currency": str(item.get("currency", "")),
                "frozen_balance": float(item.get("frozenBalance", 0) or 0),
            }
        )
    return balances, None


async def create_platega_payment(
    *,
    payment_id: str,
    amount_rub: Decimal,
    description: str,
) -> dict[str, str]:
    settings = get_settings()
    client = require_platega_client()
    base = settings.public_base_url.rstrip("/")
    return_url = settings.platega_return_url or f"{base}/payment/success"
    failed_url = settings.platega_failed_url or f"{base}/payment/failed"

    def _call() -> dict[str, str]:
        data: dict[str, object] = {
            "paymentDetails": {
                "amount": float(amount_rub),
                "currency": "RUB",
            },
            "description": description,
            "return": return_url,
            "failedUrl": failed_url,
            "payload": payment_id,
        }
        if settings.platega_payment_method > 0:
            data["paymentMethod"] = settings.platega_payment_method

        # v2 — единая форма оплаты; v1 + карты часто даёт 400 «Wrong input parameters».
        result = client._request("POST", "/v2/transaction/process", data)
        transaction_id = str(
            result.get("transactionId") or result.get("id") or ""
        )
        redirect = str(result.get("url") or result.get("redirect") or "")
        if not transaction_id or not redirect:
            raise PlategaAPIError(
                "Platega returned incomplete payment response",
                response_data=result,
            )
        return {"transaction_id": transaction_id, "redirect": redirect}

    return await asyncio.to_thread(_call)
