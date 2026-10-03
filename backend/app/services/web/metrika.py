"""Офлайн-конверсия Метрики с вебхука оплаты. Без токена - молча пропускаем."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.http import get_async_client
from app.database.models import Payment

logger = logging.getLogger(__name__)


async def report_purchase(payment: Payment) -> None:
    settings = get_settings()
    token = (settings.yandex_metrika_token or "").strip()
    if not token:
        logger.info("metrika purchase skipped: no token payment=%s", payment.id)
        return
    payload = payment.payload or {}
    client_id = str(payload.get("metrika_client_id") or "").strip()
    yclid = str(payload.get("yclid") or "").strip()
    if not client_id and not yclid:
        logger.info("metrika purchase skipped: no client id payment=%s", payment.id)
        return
    header = "ClientId,Target,DateTime,Price,Currency" if client_id else "Yclid,Target,DateTime,Price,Currency"
    who = client_id or yclid
    price = f"{payment.amount_rub:.2f}"
    stamp = int(datetime.now(UTC).timestamp())
    body = f"{header}\n{who},purchase,{stamp},{price},RUB\n"
    url = (
        f"https://api-metrika.yandex.net/management/v1/counter/"
        f"{settings.yandex_metrika_id}/offline_conversions/upload"
    )
    last_error = ""
    for attempt in range(3):
        try:
            response = await get_async_client().post(
                url,
                headers={"Authorization": f"OAuth {token}"},
                files={"file": ("conversions.csv", body.encode(), "text/csv")},
            )
            if response.status_code < 400:
                logger.info(
                    "metrika purchase ok payment=%s amount=%s attempt=%s",
                    payment.id,
                    payment.amount_rub,
                    attempt + 1,
                )
                return
            last_error = f"{response.status_code} {response.text[:300]}"
            logger.warning("metrika upload %s", last_error)
        except Exception as exc:
            last_error = str(exc)
            logger.exception("metrika upload failed payment=%s", payment.id)
        if attempt < 2:
            await asyncio.sleep(1.5 * (attempt + 1))
    logger.error("metrika upload gave up payment=%s err=%s", payment.id, last_error)
