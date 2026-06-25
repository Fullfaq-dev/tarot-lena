import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from platega import PlategaCallback

from app.core.config import get_settings
from app.database.session import AsyncSessionLocal
from app.services.billing.service import BillingService
from app.services.telegram_notify import notify_owner, send_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/callbacks/platega", tags=["platega-callbacks"])


@router.post("")
async def platega_callback(request: Request) -> PlainTextResponse:
    settings = get_settings()
    if not settings.platega_merchant_id or not settings.platega_api_key:
        raise HTTPException(status_code=503, detail="Platega is not configured")

    body = (await request.body()).decode("utf-8")
    headers = {key: value for key, value in request.headers.items()}
    callback = PlategaCallback(settings.platega_merchant_id, settings.platega_api_key)
    if not callback.validate_raw(headers, body):
        detail = callback.get_validation_error() or "Invalid callback"
        logger.warning("Platega callback rejected: %s", detail)
        raise HTTPException(status_code=401, detail=detail)

    billing = BillingService()
    notify: dict[str, int | str] | None = None
    owner_text: str | None = None
    async with AsyncSessionLocal() as session:
        try:
            result = await billing.process_platega_callback(
                session,
                transaction_id=callback.get_transaction_id() or "",
                payment_id=callback.get_order_id(),
                status=callback.get_status() or "",
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
            logger.exception("Platega callback processing failed")
            await session.rollback()
            raise HTTPException(status_code=500, detail="Callback processing failed") from None

    if notify:
        telegram_id = int(notify["telegram_id"])
        keyboard = await billing.reply_main_menu_markup(telegram_id)
        await send_telegram_message(telegram_id, str(notify["text"]), reply_markup=keyboard)

    if owner_text:
        await notify_owner(owner_text)

    return PlainTextResponse("OK")
