from pathlib import Path

from app.services.ai.context import load_system_prompt
from app.services.products.catalog import PRODUCTS
from app.services.products.packages import PACKAGES

_PROMPTS_DIR = Path(__file__).resolve().parents[4] / "prompts"


def _load(name: str) -> str:
    path = _PROMPTS_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def numerology_system() -> str:
    base = load_system_prompt("ru")
    extra = _load("numerology_ru.md")
    return f"{base}\n\n{extra}" if extra else base


def astro_system() -> str:
    base = load_system_prompt("ru")
    extra = _load("astro_ru.md")
    return f"{base}\n\n{extra}" if extra else base


def tarot_system() -> str:
    base = load_system_prompt("ru")
    extra = _load("tarot_ru.md")
    return f"{base}\n\n{extra}" if extra else base


def leia_reading_system() -> str:
    parts = [numerology_system(), _load("tarot_ru.md"), _load("astro_ru.md")]
    return "\n\n".join(p for p in parts if p)


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
