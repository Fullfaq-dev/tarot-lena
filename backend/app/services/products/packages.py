from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Package:
    id: str
    title: str
    emoji: str
    price_rub: Decimal
    pitch: str
    purpose: str


# Тест кассы 10 ₽. После проверки поставь False — пакет пропадёт с сайта и из бота.
TEST_PAYMENT_ENABLED = True

PACKAGES: dict[str, Package] = {}
if TEST_PAYMENT_ENABLED:
    PACKAGES["test_10"] = Package(
        id="test_10",
        title="Тестовый платёж",
        emoji="🧪",
        price_rub=Decimal("10"),
        purpose="test_payment",
        pitch=(
            "🧪 **Тестовый платёж** — 10 ₽\n\n"
            "Проверка Робокассы. Доступа не даёт, пакет не активирует."
        ),
    )

PACKAGES.update({
    "happy_woman": Package(
        id="happy_woman",
        title="Счастливая женщина",
        emoji="🎁",
        price_rub=Decimal("990"),
        purpose="combo_happy_woman",
        pitch=(
            "🎁 **«Счастливая женщина»** — 990 ₽ _(экономия 500 ₽)_\n\n"
            "Три главных ответа для вашей жизни:\n"
            "💞 Совместимость с партнёром (550 ₽)\n"
            "💰 Нумерологический расчёт богатства (390 ₽)\n"
            "📆 Личный прогноз на месяц (550 ₽)\n\n"
            "✔️ Полная картина жизни на ближайший месяц — всё сразу."
        ),
    ),
    "love_plus": Package(
        id="love_plus",
        title="ЛЮБОВЬ+",
        emoji="💗",
        price_rub=Decimal("1200"),
        purpose="subscription_love_plus",
        pitch=(
            "💗 **«ЛЮБОВЬ+»** — 1 200 ₽ / месяц\n\n"
            "Неограниченные полные разборы по отношениям на 30 дней:\n"
            "💞 Любовь / совместимость\n"
            "💬 Разбор переписки\n"
            "«Что он думает?», «Вернётся ли?» — сколько угодно.\n\n"
            "✔️ Личный любовный оракул в кармане."
        ),
    ),
    "vip": Package(
        id="vip",
        title="VIP-пакет",
        emoji="👑",
        price_rub=Decimal("2300"),
        purpose="subscription_vip",
        pitch=(
            "👑 **«VIP-пакет»** — 2 300 ₽ / месяц\n\n"
            "Полный доступ ко всем возможностям на 30 дней:\n"
            "✅ Любовь, переписка, деньги, прогнозы, негатив, вопросы — без лимитов\n"
            "✅ Для себя, родных и друзей\n\n"
            "✔️ Личный эзотерический помощник 24/7."
        ),
    ),
})

COMBO_PRODUCTS = ("love", "wealth", "forecast")
