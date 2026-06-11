from decimal import Decimal

FREE_CHAT_MESSAGES_PER_MONTH = 10
FREE_READINGS_PER_MONTH = 3
BILLING_CREDIT_USD = Decimal("0.007")
CHARGE_MARKUP = Decimal("50")
PROVIDER_COST_DISPLAY_MULTIPLIER = Decimal("2")
USD_TO_RUB = Decimal("92")

# Сколько прошлых реплик (user+assistant) уходит в контекст ИИ
CHAT_HISTORY_LIMITS = {
    "free": 4,
    "plus": 6,
    "premium": 8,
}

CHAT_MEMORY_LIMITS = {
    "free": 10,
    "plus": 30,
    "premium": 50,
}

SUBSCRIPTION_PRICES_RUB = {
    "plus": Decimal("999"),
    "premium": Decimal("2999"),
}

TOP_UP_AMOUNTS_RUB = [Decimal("100"), Decimal("300"), Decimal("500")]

AI_MODEL_NAME = "gpt-5-2"
AI_PROVIDER_NAME = "kie"


def memory_limit_for_tier(tier: str) -> int:
    return CHAT_MEMORY_LIMITS.get(tier, CHAT_MEMORY_LIMITS["free"])


def chat_history_limit_for_tier(tier: str) -> int:
    return CHAT_HISTORY_LIMITS.get(tier, CHAT_HISTORY_LIMITS["free"])


def is_unlimited_chat(tier: str) -> bool:
    return tier in {"plus", "premium"}


def can_use_premium_voice(tier: str) -> bool:
    return tier == "premium"


def free_messages_left(used: int) -> int:
    return max(0, FREE_CHAT_MESSAGES_PER_MONTH - used)
