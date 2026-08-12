"""Robokassa cashbox snapshot for the admin dashboard.

Robokassa merchant login/password API does not expose a live LK balance
(unlike Platega get_balances). We show shop cashflow from our payments DB
and optionally try Partner API if ROBOKASSA_PARTNER_ID is configured.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from app.core.config import get_settings
from app.database.models import Payment
from app.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def fetch_robokassa_cashbox() -> tuple[dict[str, Any], str | None]:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        completed = await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Payment.amount_rub), 0),
            ).where(
                Payment.provider == "robokassa",
                Payment.status == "completed",
            )
        )
        pending = await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Payment.amount_rub), 0),
            ).where(
                Payment.provider == "robokassa",
                Payment.status == "pending",
            )
        )
        c_count, c_sum = completed.one()
        p_count, p_sum = pending.one()

    completed_sum = Decimal(str(c_sum or 0))
    pending_sum = Decimal(str(p_sum or 0))
    data: dict[str, Any] = {
        "configured": bool(settings.robokassa_configured),
        "merchant_login": settings.robokassa_merchant_login or "",
        "is_test": bool(settings.robokassa_is_test),
        "completed_count": int(c_count or 0),
        "completed_rub": f"{completed_sum.quantize(Decimal('0.01'))}",
        "pending_count": int(p_count or 0),
        "pending_rub": f"{pending_sum.quantize(Decimal('0.01'))}",
        "available_rub": None,
        "source": "payments_db",
        "note": (
            "У Robokassa нет API баланса магазина по Password#1/#2 (как у Platega). "
            "Ниже — оборот по платежам бота. Живой остаток смотри в кабинете Robokassa."
        ),
    }

    partner_id = (getattr(settings, "robokassa_partner_id", "") or "").strip()
    if partner_id:
        live, err = await _try_partner_balance(partner_id)
        if live is not None:
            data["available_rub"] = live
            data["source"] = "partner_api"
            data["note"] = "Остаток из Partner API Robokassa."
            return data, None
        return data, err

    if not settings.robokassa_configured:
        return data, "Robokassa не настроена (ROBOKASSA_MERCHANT_LOGIN / PASSWORD1 / PASSWORD2)"
    return data, None


async def _try_partner_balance(partner_id: str) -> tuple[str | None, str | None]:
    """Best-effort: Partner API requires shop credentials we may not have."""
    import asyncio

    import httpx

    url = (
        "https://services.robokassa.ru/PartnerRegisterService/api/Shop/GetPartnerState"
        f"?roboxPartnerId={partner_id}"
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await asyncio.wait_for(client.get(url), timeout=20)
        if resp.status_code >= 400:
            return None, f"Partner API HTTP {resp.status_code}"
        # GetPartnerState has no balance field — keep DB cashflow as source of truth.
        return None, "Partner API не отдаёт баланс; показан оборот по платежам бота"
    except Exception as exc:
        logger.warning("Robokassa partner balance probe failed: %s", exc)
        return None, str(exc)
