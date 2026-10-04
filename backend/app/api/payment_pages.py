from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.models import Payment, WebReading
from app.database.session import get_session
from app.services.web.pay_return import pick_return_token, reading_return_path

router = APIRouter(tags=["payment-pages"])
_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def _bot_url(request: Request) -> str | None:
    username = getattr(request.app.state, "bot_username", None)
    if username:
        return f"https://t.me/{username.lstrip('@')}"
    return None


def _page_context(request: Request) -> dict:
    settings = get_settings()
    return {
        "bot_url": _bot_url(request),
        "support_url": settings.support_telegram_url,
        "site_url": settings.public_base_url.rstrip("/"),
    }


async def _params_from_request(request: Request) -> dict[str, str]:
    merged: dict[str, str] = {}
    for key, value in request.query_params.multi_items():
        merged[key] = value
    if request.method.upper() == "POST":
        form = await request.form()
        for key, value in form.multi_items():
            merged[str(key)] = str(value)
    return merged


async def _payment_token(session: AsyncSession, params: dict[str, str]) -> str:
    shp_id = (params.get("Shp_payment_id") or params.get("shp_payment_id") or "").strip()
    inv = (params.get("InvId") or params.get("InvID") or params.get("invid") or "").strip()
    payment = None
    if shp_id:
        payment = await session.get(Payment, shp_id)
    if payment is None and inv:
        payment = await session.scalar(
            select(Payment)
            .where(Payment.provider_payment_id == inv)
            .order_by(Payment.created_at.desc())
        )
    if payment is None:
        return ""
    return str((payment.payload or {}).get("token") or "").strip()


async def _existing_reading_token(session: AsyncSession, token: str) -> str:
    token = (token or "").strip()
    if not token:
        return ""
    found = await session.scalar(select(WebReading.token).where(WebReading.token == token))
    return str(found or "").strip()


async def _web_reading_token(
    session: AsyncSession,
    params: dict[str, str],
    *,
    cookie_token: str = "",
) -> str:
    raw = pick_return_token(
        shp_token=params.get("Shp_token") or params.get("shp_token") or "",
        payment_token=await _payment_token(session, params),
        cookie_token=cookie_token,
    )
    return await _existing_reading_token(session, raw)


@router.api_route("/payment/success", methods=["GET", "POST"], response_model=None)
async def payment_success(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    params = await _params_from_request(request)
    token = await _web_reading_token(
        session,
        params,
        cookie_token=request.cookies.get("leia_last_reading") or "",
    )
    if token:
        return RedirectResponse(reading_return_path(token), status_code=303)
    return _templates.TemplateResponse(
        request,
        "payment/success.html",
        _page_context(request),
    )


@router.get("/payment/failed", response_class=HTMLResponse)
async def payment_failed(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(
        request,
        "payment/failed.html",
        _page_context(request),
    )
