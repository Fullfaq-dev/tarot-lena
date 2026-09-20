from __future__ import annotations

import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from urllib.parse import urlencode

from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.http import get_async_client
from app.database.models import User, WebIdentity, WebReading, WebSession
from app.services.web.service import ensure_session, guest_telegram_id

COOKIE = "leia_sid"
COOKIE_DAYS = 30


def _secret() -> bytes:
    return get_settings().jwt_secret.encode("utf-8")


def sign_session(user_id: str) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + COOKIE_DAYS * 86400}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(_secret(), raw, hashlib.sha256).hexdigest()
    return urlsafe_b64encode(raw).decode("ascii") + "." + sig


def read_session(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    blob, sig = token.rsplit(".", 1)
    try:
        raw = urlsafe_b64decode(blob + "=" * (-len(blob) % 4))
    except Exception:
        return None
    expected = hmac.new(_secret(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    if int(payload.get("exp") or 0) < time.time():
        return None
    return str(payload.get("uid") or "") or None


def set_login_cookie(response: Response, user_id: str) -> None:
    secure = get_settings().public_base_url.startswith("https://")
    response.set_cookie(
        COOKIE,
        sign_session(user_id),
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=COOKIE_DAYS * 86400,
        path="/",
    )


def clear_login_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


async def user_from_request(request: Request, session: AsyncSession) -> User | None:
    uid = read_session(request.cookies.get(COOKIE))
    if not uid:
        return None
    return await session.scalar(select(User).where(User.id == uid))


def oauth_ready() -> dict[str, bool]:
    settings = get_settings()
    return {
        "yandex": bool(settings.yandex_oauth_client_id and settings.yandex_oauth_client_secret),
        "vk": bool(settings.vk_oauth_client_id and settings.vk_oauth_client_secret),
    }


def _redirect_uri(provider: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/api/web/auth/{provider}/callback"


def start_url(provider: str, *, guest_id: str, next_path: str) -> str:
    settings = get_settings()
    state = urlsafe_b64encode(
        json.dumps({"g": guest_id, "n": next_path, "p": provider}).encode()
    ).decode()
    if provider == "yandex":
        if not settings.yandex_oauth_client_id:
            raise HTTPException(400, "Яндекс OAuth не настроен")
        return "https://oauth.yandex.ru/authorize?" + urlencode(
            {
                "response_type": "code",
                "client_id": settings.yandex_oauth_client_id,
                "redirect_uri": _redirect_uri("yandex"),
                "scope": "login:info login:email",
                "state": state,
            }
        )
    if provider == "vk":
        if not settings.vk_oauth_client_id:
            raise HTTPException(400, "VK OAuth не настроен")
        return "https://oauth.vk.com/authorize?" + urlencode(
            {
                "client_id": settings.vk_oauth_client_id,
                "display": "page",
                "redirect_uri": _redirect_uri("vk"),
                "scope": "email",
                "response_type": "code",
                "v": "5.199",
                "state": state,
            }
        )
    raise HTTPException(404, "Неизвестный провайдер")


def parse_state(state: str) -> dict:
    try:
        raw = urlsafe_b64decode(state + "=" * (-len(state) % 4))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("bad state")
        return data
    except Exception as exc:
        raise HTTPException(400, "Сломан state") from exc


async def _yandex_profile(code: str) -> tuple[str, str | None, str | None]:
    settings = get_settings()
    client = get_async_client()
    try:
        token_res = await client.post(
            "https://oauth.yandex.ru/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.yandex_oauth_client_id,
                "client_secret": settings.yandex_oauth_client_secret,
            },
        )
        token_res.raise_for_status()
        access = token_res.json().get("access_token")
        info = await client.get(
            "https://login.yandex.ru/info",
            params={"format": "json"},
            headers={"Authorization": f"OAuth {access}"},
        )
        info.raise_for_status()
        body = info.json()
    except Exception as exc:
        raise HTTPException(400, "Яндекс не пустил") from exc
    subject = str(body.get("id") or body.get("psuid") or "")
    if not subject:
        raise HTTPException(400, "Яндекс не вернул профиль")
    email = body.get("default_email") or (body.get("emails") or [None])[0]
    name = body.get("display_name") or body.get("real_name") or body.get("login")
    return subject, email, name


async def _vk_profile(code: str) -> tuple[str, str | None, str | None]:
    settings = get_settings()
    client = get_async_client()
    token_res = await client.get(
        "https://oauth.vk.com/access_token",
        params={
            "client_id": settings.vk_oauth_client_id,
            "client_secret": settings.vk_oauth_client_secret,
            "redirect_uri": _redirect_uri("vk"),
            "code": code,
        },
    )
    token_res.raise_for_status()
    body = token_res.json()
    subject = str(body.get("user_id") or "")
    if not subject:
        raise HTTPException(400, "VK не вернул профиль")
    email = body.get("email")
    name = None
    access = body.get("access_token")
    if access:
        users = await client.get(
            "https://api.vk.com/method/users.get",
            params={"access_token": access, "v": "5.199"},
        )
        if users.status_code == 200:
            item = ((users.json().get("response") or [{}])[0])
            name = " ".join(p for p in [item.get("first_name"), item.get("last_name")] if p) or None
    return subject, email, name


async def upsert_oauth_user(
    session: AsyncSession,
    *,
    provider: str,
    subject: str,
    email: str | None,
    name: str | None,
    guest_id: str,
) -> User:
    ident = await session.scalar(
        select(WebIdentity).where(WebIdentity.provider == provider, WebIdentity.subject == subject)
    )
    if ident:
        user = await session.scalar(select(User).where(User.id == ident.user_id))
        if user is None:
            raise HTTPException(500, "Профиль сломан")
        if email:
            ident.email = email
        if name:
            ident.name = name
            user.first_name = name[:255]
    else:
        tid = guest_telegram_id(f"oauth:{provider}:{subject}")
        user = await session.scalar(select(User).where(User.telegram_id == tid))
        if user is None:
            user = User(telegram_id=tid, first_name=(name or "Лея")[:255], language_code="ru")
            session.add(user)
            await session.flush()
        ident = WebIdentity(
            user_id=user.id,
            provider=provider,
            subject=subject,
            email=email,
            name=name,
        )
        session.add(ident)
    web = await ensure_session(session, guest_id)
    web.user_id = user.id
    if email:
        web.email = email
    await session.flush()
    return user
