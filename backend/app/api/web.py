from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.models import User, WebReading
from app.database.session import get_session
from app.services.web import service as web
from app.services.web import auth as web_auth

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
        "oauth": web_auth.oauth_ready(),
    }


@router.get("/cards")
async def cards(session: AsyncSession = Depends(get_session)) -> dict:
    return {"cards": await web.public_catalog(session)}


@router.get("/deck")
async def deck(n: int = 7, session: AsyncSession = Depends(get_session)) -> dict:
    return {"cards": await web.random_deck(session, n=min(max(n, 1), 12))}


@router.post("/sessions")
async def sessions(
    body: SessionIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    user = await web_auth.user_from_request(request, session)
    row = await web.ensure_session(
        session,
        body.guest_id,
        utm=body.utm,
        metrika_client_id=body.metrika_client_id,
        user=user,
    )
    await session.commit()
    return {"guest_id": row.guest_id, "unlimited": bool(row.unlimited_until)}


@router.post("/readings")
async def create_reading(
    body: ReadingIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        user = await web_auth.user_from_request(request, session)
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
            user=user,
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


async def require_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    user = await web_auth.user_from_request(request, session)
    if user is None:
        raise HTTPException(status_code=401, detail="Нужно войти через Яндекс или VK")
    return user


class ChatIn(BaseModel):
    text: str
    reading_token: str | None = None
    guest_id: str | None = None


class PackageIn(BaseModel):
    package_id: str


class ProfileIn(BaseModel):
    name: str | None = None
    birth_date: str | None = None
    birth_city: str | None = None
    birth_time: str | None = None


@router.get("/auth/{provider}")
async def auth_start(
    provider: str,
    guest_id: str = Query(min_length=8, max_length=64),
    next: str = "/lk",
) -> RedirectResponse:
    next_path = next if next.startswith("/") else "/lk"
    url = await web_auth.start_url(provider, guest_id=guest_id, next_path=next_path)
    return RedirectResponse(url)


@router.get("/auth/{provider}/callback")
async def auth_callback(
    provider: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error or not code or not state:
        return RedirectResponse("/lk?auth=fail")
    data = await web_auth.consume_oauth_state(state)
    if provider == "yandex":
        subject, email, name, birth = await web_auth._yandex_profile(code)
    elif provider == "vk":
        device_id = request.query_params.get("device_id") or ""
        subject, email, name, birth = await web_auth._vk_profile(
            code,
            device_id=device_id,
            code_verifier=str(data.get("v") or ""),
            state=state,
        )
    else:
        raise HTTPException(404, "Неизвестный провайдер")
    user = await web_auth.upsert_oauth_user(
        session,
        provider=provider,
        subject=subject,
        email=email,
        name=name,
        guest_id=str(data.get("g") or "guest-unknown-xx"),
        birth=birth,
    )
    await session.commit()
    response = RedirectResponse(str(data.get("n") or "/lk"))
    web_auth.set_login_cookie(response, user.id)
    return response


@router.get("/auth/telegram/callback")
async def telegram_login_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    try:
        payload = web_auth.verify_telegram_login(
            {key: value for key, value in request.query_params.items() if value}
        )
        current = await web_auth.user_from_request(request, session)
        user = await web_auth.login_telegram_user(session, payload, current)
        await session.commit()
    except HTTPException:
        return RedirectResponse("/lk?auth=fail")
    response = RedirectResponse("/lk")
    web_auth.set_login_cookie(response, user.id)
    return response


@router.post("/auth/logout")
async def auth_logout() -> Response:
    response = Response(content='{"ok":true}', media_type="application/json")
    web_auth.clear_login_cookie(response)
    return response


@router.get("/me")
async def me(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    user = await web_auth.user_from_request(request, session)
    if user is None:
        return {
            "user": None,
            "oauth": web_auth.oauth_ready(),
            "bot_username": get_settings().telegram_bot_username,
        }
    payload = await web.cabinet_payload(session, user)
    payload["oauth"] = web_auth.oauth_ready()
    payload["bot_username"] = get_settings().telegram_bot_username
    await session.commit()
    return payload


@router.patch("/profile")
async def patch_profile(
    body: ProfileIn,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await web.upsert_soul_profile(
        session,
        user,
        name=body.name,
        birth=body.birth_date,
        birth_city=body.birth_city,
        birth_time=body.birth_time,
        overwrite=True,
    )
    await session.commit()
    payload = await web.cabinet_payload(session, user)
    payload["oauth"] = web_auth.oauth_ready()
    return payload


@router.post("/auth/telegram/start")
async def telegram_login_start(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.services.web.telegram_bind import create_login_link

    current = await web_auth.user_from_request(request, session)
    try:
        return await create_login_link(site_user_id=current.id if current else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/auth/telegram/complete")
async def telegram_login_complete(
    token: str,
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    from app.services.web.telegram_bind import finish_login_token

    uid = await finish_login_token(session, token)
    if not uid:
        return RedirectResponse("/lk?auth=fail")
    response = RedirectResponse("/lk")
    web_auth.set_login_cookie(response, uid)
    return response


@router.post("/telegram/bind")
async def telegram_bind(
    user: User = Depends(require_user),
) -> dict:
    from app.services.web.telegram_bind import create_bind_link

    return await create_bind_link(user)


@router.post("/packages/checkout")
async def package_checkout(
    body: PackageIn,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        result = await web.checkout_package(session, user, body.package_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/chat")
async def chat(
    body: ChatIn,
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        result = await web.chat_reply(session, user, text=body.text, reading_token=body.reading_token)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result

