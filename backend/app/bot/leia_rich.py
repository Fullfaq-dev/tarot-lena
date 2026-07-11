"""Rich markdown layouts and AI normalization for bot «Лея»."""

from __future__ import annotations

import re

from app.bot.formatting import prepare_rich_markdown
from app.bot.rich_layouts import markdown_table
from app.services.products.catalog import PRODUCTS
from app.services.products.packages import PACKAGES

LEIA_AI_OUTPUT_FORMAT = (
    "Формат ответа — Telegram Rich Markdown:\n"
    "- Заголовки секций: ### с эмодзи\n"
    "- Числа и показатели — таблица | Показатель | Значение |\n"
    "- Списки через маркер -\n"
    "- **жирный** для акцентов\n"
    "- На «ты», от Леи в женском роде\n"
    "- Без HTML"
)


def enrich_ai_prompt(prompt: str) -> str:
    return f"{prompt.strip()}\n\n{LEIA_AI_OUTPUT_FORMAT}"


_KV_LINE = re.compile(r"^\*\*(.+?)\*\*\s*[:\-—]\s*(.+)$")
_SECTION_EMOJI = re.compile(
    r"^([💞💰🛡️🔮💡📦👤✨🌞🔢♈⭐🎁💗👑💬👭🃏📅🌟🔔]+)\s*(.+)$"
)


def normalize_leia_rich(text: str) -> str:
    """Приводит ответ ИИ или шаблон к аккуратному Telegram Rich Markdown."""
    if not text or not text.strip():
        return text

    raw = text.replace("\r\n", "\n").strip()
    blocks = re.split(r"\n{2,}", raw)
    out: list[str] = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue

        # Блок из пар «**Ключ:** значение» → таблица
        kv_rows: list[list[str]] = []
        non_kv: list[str] = []
        for line in lines:
            m = _KV_LINE.match(line)
            if m:
                kv_rows.append([m.group(1).strip(), m.group(2).strip()])
            else:
                non_kv.append(line)

        if len(kv_rows) >= 2 and not non_kv:
            if out:
                out.append("")
            out.append(
                markdown_table(["Показатель", "Значение"], kv_rows)
            )
            continue

        if len(kv_rows) == 1 and not non_kv:
            k, v = kv_rows[0]
            if out:
                out.append("")
            out.append(f"**{k}:** {v}")
            continue

        # Первая строка — заголовок секции
        first = lines[0]
        if first.startswith("###"):
            if out:
                out.append("")
            out.extend(lines)
            continue

        section = _SECTION_EMOJI.match(first)
        if section and len(first) < 80 and not first.endswith("."):
            if out:
                out.append("")
            out.append(f"### {section.group(1)} {section.group(2).strip()}")
            out.extend(lines[1:])
            continue

        if out:
            out.append("")
        out.extend(lines)

    result = "\n".join(out).strip()
    return prepare_rich_markdown(result)


def format_leia_profile_rich(
    *,
    name: str,
    birth_date: str,
    zodiac: str,
    life_path: str,
    birth_time: str,
    birth_city: str,
    partner_birth: str | None,
    plan_label: str | None,
    product_rows: list[list[str]],
    timezone: str,
    username: str | None,
    telegram_id: int,
    member_since: str,
    has_profile: bool,
) -> str:
    parts = [
        "### 👤 Твой профиль",
        "",
        "_Здесь всё, что помогает мне делать разборы точнее_",
        "",
    ]

    if has_profile:
        profile_rows = [
            ["Имя", name],
            ["Дата рождения", birth_date],
            ["Знак зодиака", zodiac],
            ["Число пути", life_path],
            ["Время рождения", birth_time],
            ["Место рождения", birth_city],
        ]
        if partner_birth:
            profile_rows.append(["Дата рождения партнёра", partner_birth])
        parts.append(markdown_table(["О тебе", " "], profile_rows))
    else:
        parts.append("_Анкета ещё не заполнена — нажми /start_")

    parts.extend(["", "### 📦 Пакет", ""])
    if plan_label:
        parts.append(plan_label)
    else:
        parts.append("_Пока без пакета — загляни в «Пакеты и подписки»_")

    parts.extend(["", "### ✨ Разборы", ""])
    if product_rows:
        parts.append(markdown_table(["Тема", "Статус"], product_rows))
    else:
        parts.append("_Ещё не пробовала — выбери тему в меню_")

    service_rows = [["Часовой пояс", timezone]]
    if username:
        service_rows.append(["Telegram", f"@{username}"])
    service_rows.append(["ID", str(telegram_id)])
    service_rows.append(["С нами с", member_since])

    parts.extend(["", "### ⚙️ Сервис", "", markdown_table([" ", " "], service_rows)])
    return normalize_leia_rich("\n".join(parts))


def format_welcome_onboarding_rich(legal_block: str) -> str:
    rows = [[f"{p.emoji} {p.title}", _product_tagline(p.id)] for p in PRODUCTS.values()]
    return normalize_leia_rich(
        "\n".join(
            [
                "### 🔮 Привет!",
                "",
                "Я — **Лея**, твой астролог и нумеролог.",
                "",
                "Помогу разобраться в отношениях, деньгах, энергии и важных решениях — "
                "через карты, числа и звёзды.",
                "",
                markdown_table(["Тема", "О чём"], rows),
                "",
                "_Для точных разборов мне понадобятся твои данные — это займёт пару минут._",
                "",
                legal_block,
            ]
        )
    )


def format_leia_menu_rich(*, plan_label: str | None = None) -> str:
    parts = [
        "### 💫 Главное меню",
        "",
        "С возвращением! Выбери, что хочешь разобрать сегодня — я рядом.",
        "",
    ]
    if plan_label:
        parts.extend([f"_{plan_label}_", ""])

    rows = [[f"{p.emoji} {p.title}", _product_tagline(p.id)] for p in PRODUCTS.values()]
    parts.extend(
        [
            markdown_table(["Тема", "О чём"], rows),
            "",
            "_Мини-версии бесплатные · полные — в один клик_",
        ]
    )
    return normalize_leia_rich("\n".join(parts))


def _product_tagline(product_id: str) -> str:
    return {
        "love": "Что происходит в паре",
        "wealth": "Деньги и ресурсы",
        "negative": "Энергия и защита",
        "forecast": "Ближайший период",
        "question": "Любой важный вопрос",
    }.get(product_id, "")


def format_product_pitch_rich(
    product_id: str,
    *,
    access_label: str | None,
    has_plan: bool,
) -> str:
    product = PRODUCTS[product_id]
    price = int(product.price_rub)
    parts = [f"### {product.emoji} {product.title}", ""]

    if access_label:
        parts.extend(
            [
                f"✅ **У тебя уже есть доступ** — {access_label}",
                "",
                "Нажми **▶️ Запустить** — полный разбор без оплаты.",
                "",
            ]
        )
    elif has_plan and product_id in ("negative", "question"):
        parts.append(
            "_Этот разбор не входит в комбо «Счастливая женщина» — "
            "нужна отдельная оплата или VIP._"
        )
        parts.append("")

    desc = _product_description(product_id)
    parts.extend(
        [
            desc,
            "",
            markdown_table(
                [" ", " "],
                [
                    ["Мини-версия", "бесплатно, один раз"],
                    ["Полная", f"{price} ₽" if not access_label else "по пакету"],
                ],
            ),
        ]
    )
    return normalize_leia_rich("\n".join(parts))


def _product_description(product_id: str) -> str:
    return {
        "love": (
            "Разберём, что на самом деле происходит между вами: "
            "совместимость, чувства, скрытые мотивы и конкретный совет."
        ),
        "wealth": (
            "Твой денежный код: где утекают силы, куда расти "
            "и какие даты благоприятны для важных решений."
        ),
        "negative": (
            "Проверим энергетику: есть ли нагрузка, слабые зоны "
            "и что поможет почувствовать себя легче."
        ),
        "forecast": (
            "Личный прогноз по неделям: на что опереться, "
            "где быть внимательнее и какие даты выделить."
        ),
        "question": (
            "Задай любой вопрос — карты и числа подскажут, "
            "куда смотреть и что делать дальше."
        ),
    }.get(product_id, "")


def format_packages_menu_rich() -> str:
    rows = []
    for pkg in PACKAGES.values():
        tag = {
            "happy_woman": "3 полных разбора сразу",
            "love_plus": "Любовь без лимита, 30 дней",
            "vip": "Все темы без оплаты, 30 дней",
        }.get(pkg.id, "")
        rows.append([f"{pkg.emoji} {pkg.title}", f"{int(pkg.price_rub)} ₽", tag])

    singles = " · ".join(
        f"{p.title} {int(p.price_rub)} ₽" for p in PRODUCTS.values()
    )
    return normalize_leia_rich(
        "\n".join(
            [
                "### 📦 Тарифы и пакеты",
                "",
                "Пакеты выгоднее разовых покупок — выбери, что ближе сейчас.",
                "",
                markdown_table(["Пакет", "Цена", "Что даёт"], rows),
                "",
                f"**Разовые полные:** {singles}",
            ]
        )
    )


def format_package_pitch_rich(package_id: str, *, active: bool) -> str:
    pkg = PACKAGES[package_id]
    price = int(pkg.price_rub)
    parts = [f"### {pkg.emoji} {pkg.title}", ""]

    if active:
        parts.extend(
            [
                "✅ **Пакет уже активен** — выбери тему в меню и нажми **▶️ Запустить**.",
                "",
            ]
        )

    body = {
        "happy_woman": (
            "Три главных разбора в одном пакете: любовь, деньги и прогноз на месяц. "
            "Удобно, если хочешь увидеть картину целиком."
        ),
        "love_plus": (
            "Месяц безлимитных полных разборов по теме «Любовь». "
            "Для вопросов «что он думает», «вернётся ли», «куда движется пара»."
        ),
        "vip": (
            "Месяц полного доступа ко всем темам — любовь, деньги, прогноз, "
            "негатив и личные вопросы без доплат."
        ),
    }.get(package_id, "")

    parts.extend(
        [
            body,
            "",
            markdown_table(
                [" ", " "],
                [
                    ["Стоимость", f"{price} ₽"],
                    ["Срок", "30 дней" if package_id != "happy_woman" else "разовый пакет"],
                ],
            ),
        ]
    )
    return normalize_leia_rich("\n".join(parts))


def format_referral_friend_rich(link: str) -> str:
    return normalize_leia_rich(
        "\n".join(
            [
                "### 👭 Приведи подругу",
                "",
                "Поделись ссылкой — подруга получит **скидку 20%** на разборы и пакеты.",
                "",
                markdown_table(
                    [" ", " "],
                    [
                        ["Скидка подруге", "20%"],
                        ["Твоя ссылка", link],
                    ],
                ),
                "",
                "_Просто перешли ссылку — остальное сработает само_",
            ]
        )
    )
