from __future__ import annotations

import json
import re

from app.services.ai.kie_client import KieClient
from app.services.energy.catalog import STONE_BY_SLUG, STONES, Stone

_PICK_SYSTEM = (
    "Ты эксперт по камням и энергетике в Telegram-боте.\n"
    "Подбери 2–4 камня из каталога для пользователя.\n\n"
    "Правила:\n"
    "1. Если в запросе есть конкретная тема (любовь, защита, деньги, спокойствие…) — опирайся на неё.\n"
    "2. Если запрос общий («подбери камни», «что мне подходит») — опирайся на профиль soul в контексте "
    "(имя, пол, дата/место рождения, цели, беспокойства из памяти).\n"
    "3. Камни должны дополнять друг друга, не дублировать одну энергию.\n"
    "4. stone_slugs — только slug из каталога, 2–4 штуки.\n"
    "5. Ответь ТОЛЬКО JSON без markdown:\n"
    '{"stone_slugs":["slug1","slug2"],"reason_short":"одна строка почему эти камни"}'
)

_BRACELET_PICK_SYSTEM = (
    "Ты эксперт по камням, рунам и браслетам-оберегам.\n"
    "Подбери схему браслета из каталога камней.\n\n"
    "Позиции:\n"
    "- center: главный камень намерения\n"
    "- left: защита и баланс\n"
    "- right: притяжение и действие\n"
    "- clasp_stone: заземление у замка\n"
    "- clasp_rune_slug: руна заземления (fehu, algiz, isa, dagaz, othala и др. из списка рун)\n\n"
    "Учти профиль пользователя в контексте и его намерение.\n"
    "Ответь ТОЛЬКО JSON:\n"
    '{"center":"slug","left":"slug","right":"slug","clasp_stone":"slug","clasp_rune_slug":"slug",'
    '"reason_short":"одна строка"}'
)


def stones_catalog_text() -> str:
    lines = []
    for stone in STONES:
        pairs = ", ".join(stone.pairs_with)
        lines.append(
            f'{stone.slug}: {stone.name} — {stone.properties}; '
            f"energy={stone.energy}; chakra={stone.chakra}; pairs_with={pairs}"
        )
    return "\n".join(lines)


def runes_catalog_brief() -> str:
    from app.services.energy.catalog import RUNES

    return "\n".join(f"{r.slug}: {r.name} — {r.meaning}" for r in RUNES)


def stones_from_slugs(slugs: list[str]) -> list[Stone]:
    result: list[Stone] = []
    seen: set[str] = set()
    for raw in slugs:
        slug = str(raw).strip().lower()
        if not slug or slug in seen:
            continue
        stone = STONE_BY_SLUG.get(slug)
        if stone:
            result.append(stone)
            seen.add(slug)
    return result


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    for candidate in (text, *re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, flags=re.DOTALL)):
        for payload in (candidate, candidate.replace("'", '"')):
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    return {}


def _context_without_system(messages: list[dict]) -> list[dict]:
    if messages and messages[0].get("role") == "system":
        return messages[1:]
    return messages


def _resolve_slugs(parsed: dict, raw: str, *, min_count: int = 2, max_count: int = 4) -> list[str]:
    slugs_raw = parsed.get("stone_slugs") or parsed.get("stones") or []
    if not isinstance(slugs_raw, list):
        slugs_raw = []

    resolved: list[str] = []
    for item in slugs_raw:
        slug = str(item).strip().lower()
        if slug in STONE_BY_SLUG and slug not in resolved:
            resolved.append(slug)

    if len(resolved) < min_count:
        for slug in STONE_BY_SLUG:
            if slug in raw.lower() and slug not in resolved:
                resolved.append(slug)
            if len(resolved) >= max_count:
                break

    return resolved[:max_count]


async def pick_stones_with_ai(
    messages: list[dict],
    kie: KieClient,
    query: str,
) -> tuple[list[Stone], str]:
    prompt_messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": f"{_PICK_SYSTEM}\n\nКаталог:\n{stones_catalog_text()}"}],
        },
        *_context_without_system(messages),
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Запрос пользователя: {query or 'подбери камни исходя из моего профиля'}\n\n"
                        "Выбери камни. Верни только JSON."
                    ),
                }
            ],
        },
    ]

    raw = await kie.chat_completion(prompt_messages, reasoning_effort="low")
    parsed = _parse_json_response(raw)
    slugs = _resolve_slugs(parsed, raw)
    reason = str(parsed.get("reason_short", "")).strip()

    if len(slugs) >= 2:
        return stones_from_slugs(slugs), reason

    raw_retry = await kie.chat_completion(
        [
            {
                "role": "system",
                "content": [{"type": "text", "text": f"{_PICK_SYSTEM}\n\nКаталог:\n{stones_catalog_text()}"}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Предыдущий ответ не удалось разобрать. Верни только валидный JSON.\n"
                            f"Запрос: {query}\n"
                            f"Предыдущий ответ:\n{raw[:2000]}"
                        ),
                    }
                ],
            },
        ],
        reasoning_effort="low",
    )
    parsed_retry = _parse_json_response(raw_retry)
    slugs = _resolve_slugs(parsed_retry, raw_retry)
    reason = str(parsed_retry.get("reason_short", "")).strip() or reason

    if len(slugs) >= 2:
        return stones_from_slugs(slugs), reason

    raise ValueError("Не удалось подобрать камни")


async def pick_bracelet_layout_with_ai(
    messages: list[dict],
    kie: KieClient,
    query: str,
) -> tuple[dict[str, Stone], str, str]:
    """Returns stone slots dict, rune slug, reason_short."""
    from app.services.energy.catalog import RUNE_BY_SLUG

    prompt_messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"{_BRACELET_PICK_SYSTEM}\n\n"
                        f"Камни:\n{stones_catalog_text()}\n\n"
                        f"Руны:\n{runes_catalog_brief()}"
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
                    "text": (
                        f"Намерение для браслета: {query or 'баланс и защита по моему профилю'}\n"
                        "Верни только JSON."
                    ),
                }
            ],
        },
    ]

    raw = await kie.chat_completion(prompt_messages, reasoning_effort="low")
    parsed = _parse_json_response(raw)

    def _stone(key: str, fallback: str) -> Stone:
        slug = str(parsed.get(key, fallback)).strip().lower()
        return STONE_BY_SLUG.get(slug) or STONE_BY_SLUG[fallback]

    layout = {
        "center": _stone("center", "clear_quartz"),
        "left": _stone("left", "black_tourmaline"),
        "right": _stone("right", "citrine"),
        "clasp_stone": _stone("clasp_stone", "hematite"),
    }
    rune_slug = str(parsed.get("clasp_rune_slug", "algiz")).strip().lower()
    if rune_slug not in RUNE_BY_SLUG:
        rune_slug = "algiz"
    reason = str(parsed.get("reason_short", "")).strip()
    return layout, rune_slug, reason
