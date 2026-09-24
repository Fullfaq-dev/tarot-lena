from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from urllib.parse import urlencode

from fastapi import HTTPException, Request, Response
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.http import get_async_client
from app.database.models import SoulProfile, User, WebIdentity, WebReading, WebSession
from app.services.web.service import ensure_session, guest_telegram_id

COOKIE = "leia_sid"
COOKIE_DAYS = 30
_oauth_redis: Redis | None = None


async def _oauth_r() -> Redis:
    global _oauth_redis
    if _oauth_redis is None:
        _oauth_redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _oauth_redis


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48).replace("=", "")
    if len(verifier) < 43:
        verifier = (verifier + "A" * 43)[:64]
    challenge = urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    return verifier, challenge


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
    token = settings.telegram_bot_token
    return {
        "yandex": bool(settings.yandex_oauth_client_id and settings.yandex_oauth_client_secret),
        "vk": bool(settings.vk_oauth_client_id and settings.vk_oauth_client_secret),
        "telegram": bool(token and token != "replace-me" and settings.telegram_bot_username),
    }


def _redirect_uri(provider: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/api/web/auth/{provider}/callback"


async def start_url(provider: str, *, guest_id: str, next_path: str) -> str:
    settings = get_settings()
    if provider == "yandex":
        if not settings.yandex_oauth_client_id:
            raise HTTPException(400, "Яндекс OAuth не настроен")
        state = urlsafe_b64encode(
            json.dumps({"g": guest_id, "n": next_path, "p": provider}, separators=(",", ":")).encode()
        ).decode().rstrip("=")
        return "https://oauth.yandex.ru/authorize?" + urlencode(
            {
                "response_type": "code",
                "client_id": settings.yandex_oauth_client_id,
                "redirect_uri": _redirect_uri("yandex"),
                "scope": "login:info login:email login:birthday",
                "state": state,
            }
        )
    if provider == "vk":
        if not settings.vk_oauth_client_id:
            raise HTTPException(400, "VK OAuth не настроен")
        verifier, challenge = _pkce()
        state = secrets.token_hex(16)
        await (await _oauth_r()).setex(
            f"web:oauth:{state}",
            600,
            json.dumps({"g": guest_id, "n": next_path, "p": provider, "v": verifier}),
        )
        return "https://id.vk.ru/authorize?" + urlencode(
            {
                "response_type": "code",
                "client_id": settings.vk_oauth_client_id,
                "redirect_uri": _redirect_uri("vk"),
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "scope": "email",
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


async def consume_oauth_state(state: str) -> dict:
    raw = await (await _oauth_r()).get(f"web:oauth:{state}")
    if raw:
        await (await _oauth_r()).delete(f"web:oauth:{state}")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    return parse_state(state)


async def _yandex_profile(code: str) -> tuple[str, str | None, str | None, str | None]:
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
                "redirect_uri": _redirect_uri("yandex"),
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
    return subject, email, name, body.get("birthday")


async def _vk_profile(
    code: str,
    *,
    device_id: str,
    code_verifier: str,
    state: str,
) -> tuple[str, str | None, str | None, str | None]:
    settings = get_settings()
    client = get_async_client()
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "client_id": settings.vk_oauth_client_id,
        "device_id": device_id,
        "redirect_uri": _redirect_uri("vk"),
        "state": state,
    }
    if settings.vk_oauth_service_token:
        payload["service_token"] = settings.vk_oauth_service_token
    elif settings.vk_oauth_client_secret:
        payload["client_secret"] = settings.vk_oauth_client_secret
    token_res = await client.post("https://id.vk.ru/oauth2/auth", data=payload)
    body = token_res.json() if token_res.content else {}
    if token_res.status_code >= 400 or body.get("error"):
        raise HTTPException(400, body.get("error_description") or body.get("error") or "VK не пустил")
    subject = str(body.get("user_id") or "")
    access = body.get("access_token")
    email = None
    name = None
    birthday = None
    if access:
        info = await client.post(
            "https://id.vk.ru/oauth2/user_info",
            data={"client_id": settings.vk_oauth_client_id, "access_token": access},
        )
        user = (info.json() or {}).get("user") or {}
        subject = str(user.get("user_id") or subject)
        email = user.get("email")
        name = " ".join(p for p in [user.get("first_name"), user.get("last_name")] if p) or None
        birthday = user.get("birthday")
    if not subject:
        raise HTTPException(400, "VK не вернул профиль")
    return subject, email, name, birthday


async def upsert_oauth_user(
    session: AsyncSession,
    *,
    provider: str,
    subject: str,
    email: str | None,
    name: str | None,
    guest_id: str,
    birth: str | None = None,
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
    prev_id = web.user_id
    web.user_id = user.id
    if email:
        web.email = email
    from app.services.web.service import upsert_soul_profile

    if prev_id and prev_id != user.id:
        old = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == prev_id))
        if old:
            await upsert_soul_profile(
                session,
                user,
                name=old.name,
                birth=old.birth_date,
                birth_city=old.birth_city,
                birth_time=old.birth_time,
                overwrite=False,
            )
    await upsert_soul_profile(session, user, name=name, birth=birth, overwrite=False)
    await session.flush()
    return user


def verify_telegram_login(params: dict[str, str]) -> dict[str, str]:
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token or token == "replace-me":
        raise HTTPException(400, "Telegram-бот не настроен")
    their_hash = params.get("hash") or ""
    data = {key: value for key, value in params.items() if key != "hash" and value}
    check = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret = hashlib.sha256(token.encode()).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not their_hash or not hmac.compare_digest(digest, their_hash):
        raise HTTPException(400, "Подпись Telegram не сошлась")
    auth_date = int(data.get("auth_date") or "0")
    if time.time() - auth_date > 86400:
        raise HTTPException(400, "Сессия Telegram устарела")
    if not data.get("id"):
        raise HTTPException(400, "Telegram не вернул id")
    return data


async def login_telegram_user(
    session: AsyncSession,
    payload: dict[str, str],
    current: User | None,
) -> User:
    from app.services.web.telegram_bind import merge_site_and_telegram

    tg_id = int(payload["id"])
    username = (payload.get("username") or "")[:255] or None
    first_name = (payload.get("first_name") or "Лея")[:255]
    last_name = (payload.get("last_name") or "")[:255] or None
    found = await session.scalar(select(User).where(User.telegram_id == tg_id))
    site_account = current is not None and (current.telegram_id is None or current.telegram_id <= 0)

    if site_account and current is not None:
        if found and found.id != current.id:
            user = await merge_site_and_telegram(session, site=current, telegram_user=found)
        else:
            current.telegram_id = tg_id
            user = current
    elif found:
        user = found
    else:
        user = User(telegram_id=tg_id, first_name=first_name, language_code="ru")
        session.add(user)
        await session.flush()

    if username:
        user.username = username
    if first_name and (not user.first_name or user.first_name in {"Гость сайта", "Лея"}):
        user.first_name = first_name
    if last_name and not user.last_name:
        user.last_name = last_name

    subject = str(tg_id)
    ident = await session.scalar(
        select(WebIdentity).where(WebIdentity.provider == "telegram", WebIdentity.subject == subject)
    )
    if ident is None:
        session.add(
            WebIdentity(
                user_id=user.id,
                provider="telegram",
                subject=subject,
                name=" ".join(p for p in [first_name, last_name] if p) or None,
            )
        )
    elif ident.user_id != user.id:
        ident.user_id = user.id
    await session.flush()
    return user
