"""Rich markdown layouts for tarot, runes, and stones."""

from __future__ import annotations

from urllib.parse import quote

from app.bot.i18n import normalize_language, t
from app.core.config import get_settings
from app.services.energy.catalog import Stone
from app.services.energy.localize import localize_rune, localize_stone
from app.services.energy.service import DrawnRune

# Blank lines before/after --- so RichBlockDivider has breathing room.
RICH_DIVIDER = "\n\n\n\n---\n\n\n\n"

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
        ]
    )
    return "\n".join(parts) + RICH_DIVIDER + interpretation.strip()


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


def format_reading_history_rich(
    *,
    lang: str,
    page_label: str,
    hint: str,
    rows: list[list[str]],
) -> str:
    lang = normalize_language(lang)
    title = {
        "ru": "📜 История раскладов",
        "en": "📜 Reading history",
        "es": "📜 Historial de tiradas",
        "pt": "📜 Histórico de leituras",
    }.get(lang, "📜 Reading history")
    headers = {
        "ru": ["#", "Тема", "Вопрос"],
        "en": ["#", "Theme", "Question"],
        "es": ["#", "Tema", "Pregunta"],
        "pt": ["#", "Tema", "Pergunta"],
    }.get(lang, ["#", "Theme", "Question"])
    parts = [f"### {title}", "", page_label, "", hint, ""]
    if rows:
        parts.extend([markdown_table(headers, rows), ""])
    return "\n".join(parts)


def format_referral_panel_rich(
    *,
    lang: str,
    available: str,
    total: str,
    count: int,
    percent: int,
    min_withdraw: str,
    link: str,
) -> str:
    lang = normalize_language(lang)
    title = {
        "ru": "🤝 Реферальная программа",
        "en": "🤝 Referral program",
        "es": "🤝 Programa de referidos",
        "pt": "🤝 Programa de indicação",
    }.get(lang, "🤝 Referral program")
    subtitle = {
        "ru": "Приглашай друзей и получай процент с их оплат.",
        "en": "Invite friends and earn a share of their payments.",
        "es": "Invita amigos y gana un porcentaje de sus pagos.",
        "pt": "Convide amigos e ganhe uma parte dos pagamentos deles.",
    }.get(lang, "Invite friends and earn a share of their payments.")
    param_header = {
        "ru": "Показатель",
        "en": "Metric",
        "es": "Indicador",
        "pt": "Indicador",
    }.get(lang, "Metric")
    value_header = {
        "ru": "Значение",
        "en": "Value",
        "es": "Valor",
        "pt": "Valor",
    }.get(lang, "Value")
    available_label = {
        "ru": "Доступно к выводу",
        "en": "Available to withdraw",
        "es": "Disponible para retiro",
        "pt": "Disponível para saque",
    }.get(lang, "Available to withdraw")
    total_label = {
        "ru": "Всего заработано",
        "en": "Total earned",
        "es": "Total ganado",
        "pt": "Total ganho",
    }.get(lang, "Total earned")
    invited_label = {
        "ru": "Приглашено",
        "en": "Invited",
        "es": "Invitados",
        "pt": "Convidados",
    }.get(lang, "Invited")
    how_title = {
        "ru": "Как это работает",
        "en": "How it works",
        "es": "Cómo funciona",
        "pt": "Como funciona",
    }.get(lang, "How it works")
    steps = {
        "ru": (
            "1. Отправь другу свою ссылку.\n\n"
            "2. Друг регистрируется и пополняет баланс или оформляет подписку.\n\n"
            f"3. Тебе начисляется **{percent}%** с каждой его оплаты."
        ),
        "en": (
            "1. Send your link to a friend.\n\n"
            "2. They sign up and top up or subscribe.\n\n"
            f"3. You receive **{percent}%** of each payment."
        ),
        "es": (
            "1. Envía tu enlace a un amigo.\n\n"
            "2. Se registra y recarga o se suscribe.\n\n"
            f"3. Recibes **{percent}%** de cada pago."
        ),
        "pt": (
            "1. Envie seu link para um amigo.\n\n"
            "2. Ele se cadastra e recarrega ou assina.\n\n"
            f"3. Você recebe **{percent}%** de cada pagamento."
        ),
    }.get(lang, f"Share your link. You receive **{percent}%** of each payment.")
    withdraw = {
        "ru": f"💸 Вывод от **{min_withdraw}** на USDT TRC-20. Выплаты — по пятницам.",
        "en": f"💸 Withdraw from **{min_withdraw}** in USDT TRC-20. Payouts on Fridays.",
        "es": f"💸 Retiro desde **{min_withdraw}** en USDT TRC-20.",
        "pt": f"💸 Saque a partir de **{min_withdraw}** em USDT TRC-20.",
    }.get(lang, f"Withdraw from **{min_withdraw}** in USDT TRC-20.")
    link_title = {
        "ru": "Твоя ссылка",
        "en": "Your link",
        "es": "Tu enlace",
        "pt": "Seu link",
    }.get(lang, "Your link")
    return "\n\n".join(
        [
            f"### {title}",
            "",
            f"_{subtitle}_",
            "",
            markdown_table(
                [param_header, value_header],
                [
                    [available_label, available],
                    [total_label, total],
                    [invited_label, str(count)],
                ],
            ),
            "",
            f"### {how_title}",
            "",
            steps,
            "",
            withdraw,
            "",
            f"**{link_title}**",
            "",
            f"`{link}`",
        ]
    )


def format_referral_stats_rich(
    *,
    lang: str,
    joined_today: int,
    earned_today: str,
    count: int,
    total: str,
    available: str,
) -> str:
    lang = normalize_language(lang)
    headers = {
        "ru": ["Период", "Приглашено", "Заработано"],
        "en": ["Period", "Invited", "Earned"],
        "es": ["Periodo", "Invitados", "Ganado"],
        "pt": ["Período", "Convidados", "Ganho"],
    }.get(lang, ["Period", "Invited", "Earned"])
    today = {
        "ru": "Сегодня",
        "en": "Today",
        "es": "Hoy",
        "pt": "Hoje",
    }.get(lang, "Today")
    total_label = {
        "ru": "Всего",
        "en": "All time",
        "es": "Total",
        "pt": "Total",
    }.get(lang, "All time")
    available_label = {
        "ru": "Доступно к выводу",
        "en": "Available to withdraw",
        "es": "Disponible para retiro",
        "pt": "Disponível para saque",
    }.get(lang, "Available to withdraw")
    title = {
        "ru": "📊 Статистика рефералки",
        "en": "📊 Referral statistics",
        "es": "📊 Estadísticas de referidos",
        "pt": "📊 Estatísticas de indicação",
    }.get(lang, "📊 Referral statistics")
    return "\n\n".join(
        [
            f"### {title}",
            "",
            markdown_table(
                headers,
                [
                    [today, str(joined_today), earned_today],
                    [total_label, str(count), total],
                ],
            ),
            "",
            f"💵 **{available_label}:** {available}",
        ]
    )


def format_referral_list_rich(
    *,
    lang: str,
    title: str,
    page_label: str,
    sort_label: str,
    rows: list[list[str]],
) -> str:
    lang = normalize_language(lang)
    headers = {
        "ru": ["#", "Имя", "Дата", "Заработано"],
        "en": ["#", "Name", "Date", "Earned"],
        "es": ["#", "Nombre", "Fecha", "Ganado"],
        "pt": ["#", "Nome", "Data", "Ganho"],
    }.get(lang, ["#", "Name", "Date", "Earned"])
    parts = [f"### {title}", "", page_label, "", sort_label, ""]
    if rows:
        parts.extend([markdown_table(headers, rows), ""])
    return "\n".join(parts)
