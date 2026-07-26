"""Robokassa ResultURL — confirm payment and reply OK{InvId}."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.database.session import AsyncSessionLocal
from app.services.billing.robokassa_client import verify_result_signature
from app.services.billing.service import BillingService
from app.services.telegram_notify import notify_owner, send_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/callbacks/robokassa", tags=["robokassa-callbacks"])


async def _params_from_request(request: Request) -> dict[str, str]:
    merged: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        merged[key] = value
    if request.method.upper() == "POST":
        form = await request.form()
        for key, value in form.multi_items():
            merged[str(key)] = str(value)
    return merged


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/", methods=["GET", "POST"])
async def robokassa_result(request: Request) -> PlainTextResponse:
    settings = get_settings()
    if not settings.robokassa_configured:
        logger.warning("Robokassa callback while not configured")
        return PlainTextResponse("Robokassa not configured", status_code=503)

    params = await _params_from_request(request)
    inv_raw = str(params.get("InvId") or "").strip()
    if not inv_raw:
        return PlainTextResponse("bad request", status_code=400)

    if not verify_result_signature(params):
        logger.warning("Robokassa bad signature InvId=%s", inv_raw)
        return PlainTextResponse("bad sign", status_code=400)

    payment_id = str(params.get("Shp_payment_id") or "").strip() or None
    billing = BillingService()
    notify: dict[str, int | str] | None = None
    owner_text: str | None = None
    async with AsyncSessionLocal() as session:
        try:
            result = await billing.process_robokassa_callback(
                session,
                inv_id=inv_raw,
                payment_id=payment_id,
                out_sum=str(params.get("OutSum") or ""),
            )
            await session.commit()
            if isinstance(result, dict):
                raw = result.get("telegram_notify")
                if isinstance(raw, dict):
                    notify = raw
                owner_raw = result.get("owner_notify")
                if isinstance(owner_raw, str):
                    owner_text = owner_raw
        except Exception:
            logger.exception("Robokassa callback processing failed")
            await session.rollback()
            return PlainTextResponse("error", status_code=500)

    if notify:
        telegram_id = int(notify["telegram_id"])
        keyboard = await billing.reply_main_menu_markup(telegram_id, notify=notify)
        await send_telegram_message(telegram_id, str(notify["text"]), reply_markup=keyboard)

    if owner_text:
        await notify_owner(owner_text)

    return PlainTextResponse(f"OK{inv_raw}")
