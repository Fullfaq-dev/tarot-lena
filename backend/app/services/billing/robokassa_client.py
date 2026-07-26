"""Robokassa payment link + ResultURL signature (MD5)."""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from urllib.parse import urlencode

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ROBOKASSA_INDEX = "https://auth.robokassa.ru/Merchant/Index.aspx"
_INV_KEY = "robokassa:inv_id"
_redis = None


class RobokassaNotConfiguredError(RuntimeError):
    pass


def _client():
    global _redis
    if _redis is None:
        from redis.asyncio import Redis

        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


def _md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def format_out_sum(amount: Decimal) -> str:
    return f"{amount.quantize(Decimal('0.01')):.2f}"


def _shp_tail(shp: dict[str, str]) -> str:
    if not shp:
        return ""
    parts = [f"{key}={shp[key]}" for key in sorted(shp)]
    return ":" + ":".join(parts)


def payment_signature(
    *,
    merchant_login: str,
    out_sum: str,
    inv_id: int,
    password1: str,
    shp: dict[str, str] | None = None,
) -> str:
    base = f"{merchant_login}:{out_sum}:{inv_id}:{password1}"
    base += _shp_tail(shp or {})
    return _md5(base)


def result_signature(
    *,
    out_sum: str,
    inv_id: int,
    password2: str,
    shp: dict[str, str] | None = None,
) -> str:
    base = f"{out_sum}:{inv_id}:{password2}"
    base += _shp_tail(shp or {})
    return _md5(base)


async def next_invoice_id() -> int:
    return int(await _client().incr(_INV_KEY))


def build_payment_url(
    *,
    payment_id: str,
    inv_id: int,
    amount_rub: Decimal,
    description: str,
) -> str:
    settings = get_settings()
    if not settings.robokassa_configured:
        raise RobokassaNotConfiguredError("Robokassa is not configured")

    out_sum = format_out_sum(amount_rub)
    shp = {"Shp_payment_id": payment_id}
    signature = payment_signature(
        merchant_login=settings.robokassa_merchant_login,
        out_sum=out_sum,
        inv_id=inv_id,
        password1=settings.robokassa_password1,
        shp=shp,
    )
    params: dict[str, str] = {
        "MerchantLogin": settings.robokassa_merchant_login,
        "OutSum": out_sum,
        "InvId": str(inv_id),
        "Description": description[:100],
        "SignatureValue": signature,
        "Culture": "ru",
        "Shp_payment_id": payment_id,
    }
    if settings.robokassa_is_test:
        params["IsTest"] = "1"
    return f"{ROBOKASSA_INDEX}?{urlencode(params)}"


def extract_shp(params: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in params.items() if k.startswith("Shp_")}


def verify_result_signature(params: dict[str, str]) -> bool:
    settings = get_settings()
    if not settings.robokassa_configured:
        return False
    out_sum = str(params.get("OutSum") or "").strip()
    inv_raw = str(params.get("InvId") or "").strip()
    received = str(params.get("SignatureValue") or "").strip().lower()
    if not out_sum or not inv_raw or not received:
        return False
    try:
        inv_id = int(inv_raw)
    except ValueError:
        return False
    expected = result_signature(
        out_sum=out_sum,
        inv_id=inv_id,
        password2=settings.robokassa_password2,
        shp=extract_shp(params),
    ).lower()
    return expected == received
