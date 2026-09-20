from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.models import WebReading
from app.database.session import get_session
from app.services.web import service as web

router = APIRouter(prefix="/api/web", tags=["web"])


class SessionIn(BaseModel):
    guest_id: str = Field(min_length=8, max_length=64)
    utm: dict[str, str] = Field(default_factory=dict)
    metrika_client_id: str | None = None


class ReadingIn(BaseModel):
    guest_id: str
    card_id: str
    answers: list[str] = Field(default_factory=list)
    slugs: list[str] = Field(default_factory=list)
    birth: str | None = None
    birth_city: str | None = None
    birth_time: str | None = None
    partner_birth: str | None = None
    utm: dict[str, str] = Field(default_factory=dict)
    metrika_client_id: str | None = None


class CheckoutIn(BaseModel):
    tariff: str = "base"
    recur_consent: bool = False


class ContactIn(BaseModel):
    email: str | None = None
    telegram: str | None = None
    marketing: bool = False
    privacy: bool = False


class EventIn(BaseModel):
    name: str
    payload: dict = Field(default_factory=dict)


@router.get("/config")
async def web_config() -> dict:
    settings = get_settings()
    return {
        "metrika_id": settings.yandex_metrika_id,
        "bot_username": settings.telegram_bot_username,
        "legal_url": "/legal",
        "unlimited_price": 590,
    }


@router.get("/cards")
async def cards(session: AsyncSession = Depends(get_session)) -> dict:
    return {"cards": await web.public_catalog(session)}


@router.get("/deck")
async def deck(n: int = 7, session: AsyncSession = Depends(get_session)) -> dict:
    return {"cards": await web.random_deck(session, n=min(max(n, 1), 12))}


@router.post("/sessions")
async def sessions(body: SessionIn, session: AsyncSession = Depends(get_session)) -> dict:
    row = await web.ensure_session(
        session,
        body.guest_id,
        utm=body.utm,
        metrika_client_id=body.metrika_client_id,
    )
    await session.commit()
    return {"guest_id": row.guest_id, "unlimited": bool(row.unlimited_until)}


@router.post("/readings")
async def create_reading(body: ReadingIn, session: AsyncSession = Depends(get_session)) -> dict:
    try:
        reading = await web.create_reading(
            session,
            guest_id=body.guest_id,
            card_id=body.card_id,
            answers=body.answers,
            slugs=body.slugs,
            birth=body.birth,
            birth_city=body.birth_city,
            birth_time=body.birth_time,
            partner_birth=body.partner_birth,
            utm=body.utm,
            metrika_client_id=body.metrika_client_id,
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return web.public_reading(reading, include_paid=reading.status in {"paid", "ready"})


@router.get("/readings/{token}")
async def get_reading(token: str, session: AsyncSession = Depends(get_session)) -> dict:
    reading = await session.scalar(select(WebReading).where(WebReading.token == token))
    if reading is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена или истекла")
    include = reading.status in {"paid", "ready"}
    return web.public_reading(reading, include_paid=include)


@router.post("/readings/{token}/checkout")
async def checkout(token: str, body: CheckoutIn, session: AsyncSession = Depends(get_session)) -> dict:
    reading = await session.scalar(select(WebReading).where(WebReading.token == token))
    if reading is None:
        raise HTTPException(status_code=404, detail="Расчёт не найден")
    try:
        result = await web.checkout(
            session, reading, tariff=body.tariff, recur_consent=body.recur_consent
        )
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/readings/{token}/contact")
async def contact(token: str, body: ContactIn, session: AsyncSession = Depends(get_session)) -> dict:
    reading = await session.scalar(select(WebReading).where(WebReading.token == token))
    if reading is None:
        raise HTTPException(status_code=404, detail="Расчёт не найден")
    await web.save_contact(
        session,
        reading,
        email=body.email,
        telegram=body.telegram,
        marketing=body.marketing,
        privacy=body.privacy,
    )
    await session.commit()
    return {"ok": True}


@router.post("/events")
async def events(body: EventIn) -> dict:
    return {"ok": True, "name": body.name}
