from __future__ import annotations

import json
import re

from app.bot.i18n import normalize_language, t
from app.bot.i18n_ai import (
    pick_bracelet_system,
    pick_bracelet_user,
    pick_stones_retry,
    pick_stones_system,
    pick_stones_user,
)
from app.services.ai.kie_client import KieClient
from app.services.energy.catalog import STONE_BY_SLUG, Stone
from app.services.energy.localize import runes_catalog_text, stones_catalog_text


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
    lang: str = "ru",
) -> tuple[list[Stone], str]:
    lang = normalize_language(lang)
    catalog = stones_catalog_text(lang)
    prompt_messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": pick_stones_system(lang, catalog)}],
        },
        *_context_without_system(messages),
        {
            "role": "user",
            "content": [{"type": "text", "text": pick_stones_user(lang, query)}],
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
                "content": [{"type": "text", "text": pick_stones_system(lang, catalog)}],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": pick_stones_retry(lang, query, raw)}],
            },
        ],
        reasoning_effort="low",
    )
    parsed_retry = _parse_json_response(raw_retry)
    slugs = _resolve_slugs(parsed_retry, raw_retry)
    reason = str(parsed_retry.get("reason_short", "")).strip() or reason

    if len(slugs) >= 2:
        return stones_from_slugs(slugs), reason

    raise ValueError(t("stone_pick_failed", lang))


async def pick_bracelet_layout_with_ai(
    messages: list[dict],
    kie: KieClient,
    query: str,
    lang: str = "ru",
) -> tuple[dict[str, Stone], str, str]:
    """Returns stone slots dict, rune slug, reason_short."""
    from app.services.energy.catalog import RUNE_BY_SLUG

    lang = normalize_language(lang)
    stones_text = stones_catalog_text(lang)
    runes_text = runes_catalog_text(lang)

    prompt_messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": pick_bracelet_system(lang, stones_text, runes_text)},
            ],
        },
        *_context_without_system(messages),
        {
            "role": "user",
            "content": [{"type": "text", "text": pick_bracelet_user(lang, query)}],
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
