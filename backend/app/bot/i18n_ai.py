"""Localized AI prompts for orchestrator, stone picker, and vision."""

from __future__ import annotations

from app.bot.i18n import normalize_language, t


def zen_ai_prompt(lang: str, text: str) -> str:
    lang = normalize_language(lang)
    return t("ai_zen_prompt", lang, text=text)


def zen_stored_user(lang: str, text: str) -> str:
    return t("ai_zen_stored", normalize_language(lang), text=text)


def rune_ai_prompt(lang: str, question: str, rune_lines: str) -> str:
    return t("ai_rune_prompt", normalize_language(lang), question=question, runes=rune_lines)


def rune_stored_user(lang: str, question: str, names: str) -> str:
    return t("ai_rune_stored", normalize_language(lang), question=question, names=names)


def stone_ai_prompt(lang: str, query: str, stone_lines: str, pick_reason: str = "") -> str:
    lang = normalize_language(lang)
    reason_hint = t("ai_stone_reason_hint", lang, reason=pick_reason) if pick_reason else ""
    query_text = query or t("ai_stone_default_query", lang)
    return t("ai_stone_prompt", lang, reason_hint=reason_hint, query=query_text, stones=stone_lines)


def stone_stored_user(lang: str, query: str, names: str) -> str:
    lang = normalize_language(lang)
    q = query or t("ai_stone_profile_short", lang)
    return t("ai_stone_stored", lang, query=q, names=names)


def bracelet_ai_prompt(lang: str, query: str, layout_lines: str, pick_reason: str = "") -> str:
    lang = normalize_language(lang)
    reason_hint = t("ai_bracelet_reason_hint", lang, reason=pick_reason) if pick_reason else ""
    query_text = query or t("ai_bracelet_default_query", lang)
    return t("ai_bracelet_prompt", lang, reason_hint=reason_hint, query=query_text, layout=layout_lines)


def bracelet_stored_user(lang: str, query: str) -> str:
    lang = normalize_language(lang)
    q = query or t("ai_bracelet_profile_short", lang)
    return t("ai_bracelet_stored", lang, query=q)


def tarot_ai_prompt(lang: str, reading_type: str, question: str, card_lines: str) -> str:
    return t(
        "ai_tarot_prompt",
        normalize_language(lang),
        reading_type=reading_type,
        question=question,
        cards=card_lines,
    )


def tarot_stored_user(lang: str, label: str, question: str, card_names: str) -> str:
    return t(
        "ai_tarot_stored",
        normalize_language(lang),
        label=label,
        question=question,
        cards=card_names,
    )


def pick_stones_system(lang: str, catalog: str) -> str:
    return t("ai_pick_stones_system", normalize_language(lang), catalog=catalog)


def pick_stones_user(lang: str, query: str) -> str:
    lang = normalize_language(lang)
    q = query or t("ai_pick_stones_default_query", lang)
    return t("ai_pick_stones_user", lang, query=q)


def pick_stones_retry(lang: str, query: str, raw: str) -> str:
    return t("ai_pick_stones_retry", normalize_language(lang), query=query, raw=raw[:2000])


def pick_bracelet_system(lang: str, stones: str, runes: str) -> str:
    return t("ai_pick_bracelet_system", normalize_language(lang), stones=stones, runes=runes)


def pick_bracelet_user(lang: str, query: str) -> str:
    lang = normalize_language(lang)
    q = query or t("ai_pick_bracelet_default_query", lang)
    return t("ai_pick_bracelet_user", lang, query=q)


def vision_json_system(lang: str) -> str:
    return t("ai_vision_json_system", normalize_language(lang))


def vision_analysis_prompt(lang: str, mode: str) -> str:
    key = f"ai_vision_analysis_{mode}"
    return t(key, normalize_language(lang))


def vision_image_base(lang: str) -> str:
    return t("ai_vision_image_base", normalize_language(lang))
