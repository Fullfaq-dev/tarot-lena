from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings

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
        "request": request,
        "bot_url": _bot_url(request),
        "support_url": settings.support_telegram_url,
        "site_url": settings.public_base_url.rstrip("/"),
    }


@router.get("/payment/success", response_class=HTMLResponse)
async def payment_success(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(
        "payment/success.html",
        _page_context(request),
    )


@router.get("/payment/failed", response_class=HTMLResponse)
async def payment_failed(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(
        "payment/failed.html",
        _page_context(request),
    )
