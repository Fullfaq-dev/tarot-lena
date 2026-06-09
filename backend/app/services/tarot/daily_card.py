import json
import re

from app.services.ai.kie_client import KieClient
from app.services.tarot.cards import FULL_DECK

_DAILY_JSON_SYSTEM = (
    "Ты таролог в Telegram. Выбери одну карту дня для пользователя с учётом его профиля и контекста.\n"
    "Ответь ТОЛЬКО JSON без markdown-обёртки:\n"
    '{"card_slug":"точный_slug", "interpretation":"2-4 персональных предложения по-русски с markdown **жирный** *курсив*"}\n'
    "card_slug должен быть ТОЧНО из списка колоды ниже."
)

_SLUG_BY_NAME = {str(card["name"]).lower(): str(card["slug"]) for card in FULL_DECK}
_VALID_SLUGS = {str(card["slug"]) for card in FULL_DECK}


def deck_catalog_text() -> str:
    return "\n".join(f'{card["slug"]}: {card["name"]}' for card in FULL_DECK)


def card_by_slug(slug: str) -> dict | None:
    normalized = slug.strip().lower()
    for card in FULL_DECK:
        if str(card["slug"]).lower() == normalized:
            return dict(card)
    return None


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    candidates = [text]
    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, flags=re.DOTALL):
        candidates.append(match.group(0))

    for candidate in candidates:
        for payload in (candidate, candidate.replace("'", '"')):
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    return {}


def _resolve_slug(parsed: dict, raw: str) -> str | None:
    slug = str(parsed.get("card_slug", "")).strip().lower()
    if slug in _VALID_SLUGS:
        return slug

    name = str(parsed.get("card_name", "")).strip().lower()
    if name in _SLUG_BY_NAME:
        return _SLUG_BY_NAME[name]

    for valid_slug in _VALID_SLUGS:
        if valid_slug in raw.lower():
            return valid_slug
    return None


def _context_without_system(messages: list[dict]) -> list[dict]:
    if messages and messages[0].get("role") == "system":
        return messages[1:]
    return messages


async def pick_daily_card_with_ai(messages: list[dict], kie: KieClient) -> tuple[dict, str]:
    prompt_messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": f"{_DAILY_JSON_SYSTEM}\n\nКолода:\n{deck_catalog_text()}",
                }
            ],
        },
        *_context_without_system(messages),
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Выбери карту дня на сегодня для этого пользователя. "
                        "Учти профиль, память и недавний контекст. "
                        "Верни только JSON с card_slug и interpretation."
                    ),
                }
            ],
        },
    ]

    raw = await kie.chat_completion(prompt_messages)
    parsed = _parse_json_response(raw)
    interpretation = str(parsed.get("interpretation", "")).strip()
    slug = _resolve_slug(parsed, raw)

    if slug:
        card = card_by_slug(slug)
        if card and interpretation:
            return card, interpretation

    retry_messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": f"{_DAILY_JSON_SYSTEM}\n\nКолода:\n{deck_catalog_text()}"}],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Предыдущий ответ не удалось разобрать. Верни только JSON.\n"
                        f"Предыдущий ответ:\n{raw[:2500]}"
                    ),
                }
            ],
        },
    ]
    raw_retry = await kie.chat_completion(retry_messages)
    parsed_retry = _parse_json_response(raw_retry)
    interpretation = str(parsed_retry.get("interpretation", "")).strip()
    slug = _resolve_slug(parsed_retry, raw_retry)
    if slug:
        card = card_by_slug(slug)
        if card and interpretation:
            return card, interpretation

    raise ValueError("Не удалось выбрать карту дня")
