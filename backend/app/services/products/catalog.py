from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Product:
    id: str
    title: str
    emoji: str
    price_rub: Decimal
    pitch: str
    mini_hint: str


PRODUCTS: dict[str, Product] = {
    "love": Product(
        id="love",
        title="Любовь",
        emoji="💞",
        price_rub=Decimal("550"),
        pitch=(
            "❤️ **Любовь** — 550 ₽\n\n"
            "Узнайте, что на самом деле происходит в вашей паре. "
            "Совместимость по датам, кармический аркан, астрологический аспект и конкретный совет.\n\n"
            "✔️ Итог: вы перестанете гадать и начнёте понимать своего мужчину."
        ),
        mini_hint="Напиши дату рождения партнёра — **ДД.ММ.ГГГГ** (например, 15.06.1990):",
    ),
    "wealth": Product(
        id="wealth",
        title="Деньги",
        emoji="💰",
        price_rub=Decimal("390"),
        pitch=(
            "💰 **Нумерологический расчёт богатства** — 390 ₽\n\n"
            "Ваше личное число богатства, «чёрные дыры» бюджета, топ-3 сферы заработка "
            "и удачные даты для трат на 3 месяца.\n\n"
            "✔️ Итог: деньги начнут приходить легче."
        ),
        mini_hint="Краткий денежный код по твоей дате рождения — смотрю числа…",
    ),
    "negative": Product(
        id="negative",
        title="Негатив",
        emoji="🛡️",
        price_rub=Decimal("300"),
        pitch=(
            "🛡️ **Есть ли на мне негатив?** — 300 ₽\n\n"
            "Диагностика 5 сфер, индекс чистоты поля и персональный совет.\n\n"
            "⚠️ Это инструмент самопознания, не медицинский диагноз."
        ),
        mini_hint="Быстрая проверка энергетики по твоей дате рождения.",
    ),
    "forecast": Product(
        id="forecast",
        title="Личный прогноз",
        emoji="🔮",
        price_rub=Decimal("550"),
        pitch=(
            "📆 **Личный прогноз на месяц** — 550 ₽\n\n"
            "Поэтапный прогноз на 4 недели, благоприятные даты, аркан-покровитель месяца.\n\n"
            "✔️ Итог: вы на шаг впереди событий."
        ),
        mini_hint="Мини-прогноз на ближайшую неделю — по твоей дате и знаку.",
    ),
    "question": Product(
        id="question",
        title="Ответ на вопрос",
        emoji="💡",
        price_rub=Decimal("500"),
        pitch=(
            "💡 **Ответ на вопрос** — 500 ₽\n\n"
            "Задайте любой вопрос — карты и нумерология подскажут, что делать дальше."
        ),
        mini_hint="Напиши вопрос, который тебя волнует — отвечу через карты и числа:",
    ),
}


def product_purpose(product_id: str) -> str:
    return f"product_{product_id}_full"


def all_product_buttons() -> list[tuple[str, str]]:
    return [(p.emoji, p.id) for p in PRODUCTS.values()]
