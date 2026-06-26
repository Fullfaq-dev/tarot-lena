import json
import re

from app.bot.i18n import normalize_language
from app.services.ai.kie_client import KieClient
from app.services.tarot.cards import FULL_DECK

_LANGUAGE_NAMES = {
    "ru": "Russian",
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese",
}

_DAILY_JSON_SYSTEM = {
    "ru": (
        "Ты таролог в Telegram. Выбери одну карту дня для пользователя с учётом его профиля и контекста.\n"
        "Ответь ТОЛЬКО JSON без markdown-обёртки:\n"
        '{"card_slug":"точный_slug", "interpretation":"2-4 персональных предложения по-русски с markdown **жирный** *курсив*"}\n'
        "card_slug должен быть ТОЧНО из списка колоды ниже."
    ),
    "en": (
        "You are a Telegram tarot reader. Pick one daily card for the user based on their profile and context.\n"
        "Reply ONLY with JSON, without a markdown wrapper:\n"
        '{"card_slug":"exact_slug", "interpretation":"2-4 personal sentences in English with markdown **bold** *italic*"}\n'
        "card_slug must be EXACTLY one slug from the deck list below."
    ),
    "es": (
        "Eres tarotista en Telegram. Elige una carta del día para el usuario según su perfil y contexto.\n"
        "Responde SOLO JSON, sin bloque markdown:\n"
        '{"card_slug":"slug_exacto", "interpretation":"2-4 frases personales en español con markdown **negrita** *cursiva*"}\n'
        "card_slug debe ser EXACTAMENTE un slug de la lista de cartas."
    ),
    "pt": (
        "Você é tarólogo no Telegram. Escolha uma carta do dia para o usuário considerando perfil e contexto.\n"
        "Responda SOMENTE JSON, sem bloco markdown:\n"
        '{"card_slug":"slug_exato", "interpretation":"2-4 frases pessoais em português com markdown **negrito** *itálico*"}\n'
        "card_slug deve ser EXATAMENTE um slug da lista do baralho."
    ),
}

_DAILY_USER_PROMPT = {
    "ru": (
        "Выбери карту дня на сегодня для этого пользователя. "
        "Учти профиль, память и недавний контекст. "
        "Верни только JSON с card_slug и interpretation."
    ),
    "en": (
        "Pick today's daily card for this user. "
        "Use their profile, memory, and recent context. "
        "Return only JSON with card_slug and interpretation."
    ),
    "es": (
        "Elige la carta del día de hoy para este usuario. "
        "Ten en cuenta su perfil, memoria y contexto reciente. "
        "Devuelve solo JSON con card_slug e interpretation."
    ),
    "pt": (
        "Escolha a carta do dia de hoje para este usuário. "
        "Considere perfil, memória e contexto recente. "
        "Retorne apenas JSON com card_slug e interpretation."
    ),
}

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


async def pick_daily_card_with_ai(
    messages: list[dict],
    kie: KieClient,
    *,
    lang: str = "ru",
) -> tuple[dict, str]:
    lang = normalize_language(lang)
    system_text = _DAILY_JSON_SYSTEM.get(lang, _DAILY_JSON_SYSTEM["en"])
    user_text = _DAILY_USER_PROMPT.get(lang, _DAILY_USER_PROMPT["en"])
    language_name = _LANGUAGE_NAMES.get(lang, "English")
    prompt_messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"{system_text}\n\n"
                        f"Important: interpretation language must be {language_name}.\n\n"
                        f"Deck:\n{deck_catalog_text()}"
                    ),
                }
            ],
        },
        *_context_without_system(messages),
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_text,
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
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"{system_text}\n\n"
                        f"Important: interpretation language must be {language_name}.\n\n"
                        f"Deck:\n{deck_catalog_text()}"
                    ),
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "The previous response could not be parsed. Return only JSON "
                        f"and keep interpretation in {language_name}.\n"
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
