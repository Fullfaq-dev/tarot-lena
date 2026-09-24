"""Live KIE credit balance for the admin dashboard."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.core.http import get_async_client

logger = logging.getLogger(__name__)


def _parse_credits(data: Any) -> float | None:
    if data is None:
        return None
    if isinstance(data, (int, float)):
        return float(data)
    if isinstance(data, str):
        try:
            return float(data.replace(",", ".").strip())
        except ValueError:
            return None
    if isinstance(data, dict):
        for key in ("credits", "credit", "balance", "remaining", "data"):
            if key in data:
                parsed = _parse_credits(data[key])
                if parsed is not None:
                    return parsed
    return None


async def fetch_kie_credits() -> tuple[dict[str, Any], str | None]:
    settings = get_settings()
    openai_key = (settings.openai_api_key or "").strip()
    openai_on = bool(openai_key) and openai_key != "replace-me"
    payload: dict[str, Any] = {
        "configured": bool(settings.kie_api_key and settings.kie_api_key != "replace-me"),
        "chat_provider": "openai" if openai_on else "kie",
        "chat_model": (settings.openai_chat_model if openai_on else settings.kie_chat_model),
        "model": (settings.openai_chat_model if openai_on else settings.kie_chat_model),
        "fallback_provider": "" if openai_on else "302.ai",
        "fallback_model": "" if openai_on else settings.ai302_chat_model,
        "credits": None,
    }
    if not payload["configured"]:
        return payload, "KIE_API_KEY не настроен"

    try:
        client = get_async_client()
        response = await client.get(
            f"{settings.kie_base_url.rstrip('/')}/api/v1/chat/credit",
            headers={"Authorization": f"Bearer {settings.kie_api_key}"},
            timeout=15,
        )
        response.raise_for_status()
        body = response.json()
    except Exception as exc:
        logger.warning("KIE credits fetch failed: %s", exc)
        return payload, f"Не удалось получить баланс KIE: {exc}"

    code = body.get("code")
    if isinstance(code, int) and code not in (0, 200):
        return payload, body.get("msg") or f"KIE credit code {code}"

    credits = _parse_credits(body.get("data"))
    if credits is None:
        credits = _parse_credits(body)
    if credits is None:
        return payload, body.get("msg") or "KIE не вернул число кредитов"

    payload["credits"] = round(credits, 4)
    return payload, None
