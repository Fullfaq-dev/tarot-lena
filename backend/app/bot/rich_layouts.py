"""Rich markdown layouts for tarot, runes, and stones."""

from __future__ import annotations

from urllib.parse import quote

from app.bot.i18n import normalize_language, t
from app.core.config import get_settings
from app.services.energy.catalog import Stone
from app.services.energy.localize import localize_rune, localize_stone
from app.services.energy.service import DrawnRune

_READING_POSITIONS: dict[str, dict[str, list[str]]] = {
    "day": {
        "ru": ["Карта дня"],
        "en": ["Card of the day"],
        "es": ["Carta del día"],
        "pt": ["Carta do dia"],
    },
    "week": {
        "ru": ["Начало", "Середина", "Итог"],
        "en": ["Beginning", "Middle", "Outcome"],
        "es": ["Inicio", "Mitad", "Resultado"],
        "pt": ["Início", "Meio", "Resultado"],
    },
    "month": {
        "ru": ["Общий фон", "Препятствие", "Совет", "Влияние", "Итог"],
        "en": ["Overview", "Obstacle", "Advice", "Influence", "Outcome"],
        "es": ["Panorama", "Obstáculo", "Consejo", "Influencia", "Resultado"],
        "pt": ["Panorama", "Obstáculo", "Conselho", "Influência", "Resultado"],
    },
    "love": {
        "ru": ["Ты", "Партнёр", "Развитие"],
        "en": ["You", "Partner", "Development"],
        "es": ["Tú", "Pareja", "Desarrollo"],
        "pt": ["Você", "Parceiro(a)", "Desenvolvimento"],
    },
    "relationship": {
        "ru": ["Ты", "Партнёр", "Связь", "Препятствие", "Совет"],
        "en": ["You", "Partner", "Bond", "Obstacle", "Advice"],
        "es": ["Tú", "Pareja", "Vínculo", "Obstáculo", "Consejo"],
        "pt": ["Você", "Parceiro(a)", "Vínculo", "Obstáculo", "Conselho"],
    },
    "money": {
        "ru": ["Ситуация", "Действие", "Результат"],
        "en": ["Situation", "Action", "Outcome"],
        "es": ["Situación", "Acción", "Resultado"],
        "pt": ["Situação", "Ação", "Resultado"],
    },
    "career": {
        "ru": ["Сейчас", "Путь", "Перспектива"],
        "en": ["Now", "Path", "Outlook"],
        "es": ["Ahora", "Camino", "Perspectiva"],
        "pt": ["Agora", "Caminho", "Perspectiva"],
    },
    "choice": {
        "ru": ["Вариант А", "Вариант Б"],
        "en": ["Option A", "Option B"],
        "es": ["Opción A", "Opción B"],
        "pt": ["Opção A", "Opção B"],
    },
    "past_present_future": {
        "ru": ["Прошлое", "Настоящее", "Будущее"],
        "en": ["Past", "Present", "Future"],
        "es": ["Pasado", "Presente", "Futuro"],
        "pt": ["Passado", "Presente", "Futuro"],
    },
    "compatibility": {
        "ru": ["Вы", "Партнёр", "Энергия", "Сильные стороны", "Вызов", "Потенциал"],
        "en": ["You", "Partner", "Energy", "Strengths", "Challenge", "Potential"],
        "es": ["Tú", "Pareja", "Energía", "Fortalezas", "Desafío", "Potencial"],
        "pt": ["Você", "Parceiro(a)", "Energia", "Forças", "Desafio", "Potencial"],
    },
}


def _escape_table_cell(text: str) -> str:
    return " ".join(str(text).replace("|", "/").split())


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header_line = "| " + " | ".join(_escape_table_cell(h) for h in headers) + " |"
    sep_line = "| " + " | ".join(":---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header_line, sep_line, *body])


def tarot_collage_available() -> bool:
    base = get_settings().public_base_url.lower()
    return not any(host in base for host in ("localhost", "127.0.0.1", "0.0.0.0"))


def card_image_public_url(card: dict) -> str | None:
    image_file = card.get("image_file")
    if not image_file:
        return None
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/static/tarot_cards/{quote(str(image_file))}"


def reading_position_labels(reading_type: str, count: int, lang: str) -> list[str]:
    lang = normalize_language(lang)
    labels = _READING_POSITIONS.get(reading_type, {}).get(lang)
    if not labels:
        labels = _READING_POSITIONS.get(reading_type, {}).get("en", [])
    if labels and len(labels) >= count:
        return labels[:count]
    generic = t("reading_position_n", lang)
    return [generic.format(n=i + 1) for i in range(count)]


def format_tarot_collage(cards: list[dict]) -> str:
    urls = [url for card in cards if (url := card_image_public_url(card))]
    if not urls:
        return ""
    lines = ["<tg-collage>", ""]
    lines.extend(f"![]({url})" for url in urls)
    lines.extend(["", "</tg-collage>", ""])
    return "\n".join(lines)


def format_tarot_reading_rich(
    *,
    label: str,
    question: str,
    cards: list[dict],
    reading_type: str,
    interpretation: str,
    lang: str,
    include_collage: bool = True,
) -> str:
    lang = normalize_language(lang)
    positions = reading_position_labels(reading_type, len(cards), lang)
    rows = [
        [positions[index], str(card.get("name", ""))]
        for index, card in enumerate(cards)
    ]
    parts = [
        f"### {label}",
        "",
        f"**{t('reading_question_label', lang)}:** {question}",
        "",
    ]
    if include_collage and tarot_collage_available():
        collage = format_tarot_collage(cards)
        if collage:
            parts.append(collage)
    parts.extend(
        [
            markdown_table(
                [t("table_position", lang), t("table_card", lang)],
                rows,
            ),
            "",
            "---",
            "",
            interpretation.strip(),
        ]
    )
    return "\n".join(parts)


def format_runes_table_rich(
    drawn: list[DrawnRune],
    lang: str,
    *,
    header: str | None = None,
    question: str | None = None,
) -> str:
    lang = normalize_language(lang)
    rows: list[list[str]] = []
    for item in drawn:
        rune = localize_rune(item.rune, lang)
        suffix = t("rune_reversed_suffix", lang) if item.reversed else ""
        rows.append([f"{rune.name}{suffix}", rune.meaning, rune.energy])

    parts: list[str] = []
    title = header or t("rune_result_header", lang)
    parts.extend([f"### {title}", ""])
    if question:
        parts.extend([f"**{t('reading_question_label', lang)}:** {question}", ""])
    parts.extend(
        [
            markdown_table(
                [t("table_rune", lang), t("table_meaning", lang), t("table_energy", lang)],
                rows,
            ),
            "",
        ]
    )
    return "\n".join(parts)


def format_stones_table_rich(
    stones: list[Stone],
    lang: str,
    *,
    header: str | None = None,
    question: str | None = None,
    reason: str = "",
) -> str:
    lang = normalize_language(lang)
    rows: list[list[str]] = []
    for stone in stones:
        loc = localize_stone(stone, lang)
        rows.append([loc.name, loc.properties, loc.chakra])

    parts: list[str] = []
    title = header or t("stone_result_header", lang)
    parts.extend([f"### {title}", ""])
    if question:
        parts.extend([f"**{t('reading_question_label', lang)}:** {question}", ""])
    parts.extend(
        [
            markdown_table(
                [t("table_stone", lang), t("table_properties", lang), t("table_chakra", lang)],
                rows,
            ),
            "",
        ]
    )
    if reason:
        parts.extend([f"_{reason}_", ""])
    return "\n".join(parts)
