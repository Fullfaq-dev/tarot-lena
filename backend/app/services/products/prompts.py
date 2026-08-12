"""Сборка промптов Леи: ОСНОВНОЙ + БЛОК (переменные только во втором)."""

from __future__ import annotations

import re
from pathlib import Path

from app.services.ai.context import load_system_prompt
from app.services.products.catalog import PRODUCTS
from app.services.products.packages import PACKAGES

_PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"
_LEIA_DIR = _PROMPTS_DIR / "leia"

# product_id → (full_block, mini_block)
PRODUCT_BLOCKS: dict[str, tuple[str, str]] = {
    "love": ("full_love", "mini_love"),
    "question": ("full_question", "mini_question"),
    "tarot_spread": ("full_tarot", "mini_tarot"),
    "wealth": ("full_wealth", "mini_wealth"),
    "forecast": ("full_matrix", "mini_matrix"),
    "negative": ("full_negative", "mini_negative"),
}

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _load(name: str) -> str:
    path = _PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _load_leia(block: str) -> str:
    path = _LEIA_DIR / f"{block}.md"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def main_system_prompt() -> str:
    """Часть 1 — без переменных, всегда первой (кэш)."""
    return load_system_prompt("ru")


def fill_placeholders(template: str, variables: dict[str, str | int]) -> str:
    """Подставляет {key}; неизвестные плейсхолдеры оставляет как есть."""
    if not template:
        return ""
    safe = {k: str(v) for k, v in variables.items()}

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return safe.get(key, match.group(0))

    return _PLACEHOLDER.sub(repl, template)


def assemble_system(block: str, variables: dict[str, str | int] | None = None) -> str:
    """system_prompt = ОСНОВНОЙ + '\\n\\n' + БЛОК (с подстановкой)."""
    main = main_system_prompt()
    body = _load_leia(block)
    if variables:
        body = fill_placeholders(body, variables)
    if not body:
        return main
    return f"{main}\n\n{body}"


def product_system(product_id: str, *, level: str, variables: dict[str, str | int]) -> str:
    pair = PRODUCT_BLOCKS.get(product_id)
    if not pair:
        return main_system_prompt()
    block = pair[0] if level == "full" else pair[1]
    return assemble_system(block, variables)


def user_trigger(product_title: str = "разбор") -> str:
    return (
        f"Сделай {product_title} строго по блоку инструкции выше. "
        "Отвечай только текстом разбора, без преамбулы."
    )


def numerology_system() -> str:
    return main_system_prompt()


def astro_system() -> str:
    return main_system_prompt()


def tarot_system() -> str:
    return main_system_prompt()


def leia_reading_system() -> str:
    """Чат и follow-up: только основной промпт (без продуктового блока)."""
    return main_system_prompt()


def leia_menu_navigation_block() -> str:
    """Catalog for chat AI — help navigate, never invent new menu items."""
    product_lines = []
    for p in PRODUCTS.values():
        product_lines.append(
            f"- {p.emoji} {p.title} — {p.price_rub} ₽ (сначала бесплатное мини, потом полная)"
        )
    package_lines = []
    for pkg in PACKAGES.values():
        package_lines.append(f"- {pkg.emoji} {pkg.title} — {pkg.price_rub} ₽")
    return (
        "### Меню бота «Лея» (навигация)\n"
        "Нижние кнопки: 🏠 Меню · 📜 История · 👤 Профиль.\n"
        "В меню (🏠 Меню):\n"
        + "\n".join(product_lines)
        + "\n- 📜 История разборов\n"
        "- 📦 Пакеты и подписки:\n"
        + "\n".join(f"  {line}" for line in package_lines)
        + "\n- 👭 Приведи подругу (реферал)\n\n"
        "Правила чата:\n"
        "- Помогай найти нужную кнопку и коротко объясни, что внутри.\n"
        "- Не делай новый расклад/матрицу/полный разбор прямо в чате — "
        "попроси открыть нужный пункт меню и нажать мини или полную версию.\n"
        "- Обсуждай прошлые разборы только если в контексте есть текст разбора "
        "и доступ разрешён; не выдумывай карты и числа."
    )
