from decimal import Decimal

from app.core.config import get_settings
from app.services.billing.limits import USD_TO_RUB

# KIE gpt-5-2: 87.5 cr/1M input, 700 cr/1M output
# Себестоимость: 1 credit = $0.005 (kie_credit_usd)
# Списание с пользователя: credits × $0.007 × markup → ₽


def _kie_credit_usd() -> Decimal:
    return Decimal(str(get_settings().kie_credit_usd))


def _billing_credit_usd() -> Decimal:
    return Decimal(str(get_settings().billing_credit_usd))


def _charge_markup() -> Decimal:
    return Decimal(str(get_settings().charge_markup))


def _input_credits_per_1m() -> Decimal:
    return Decimal(str(get_settings().kie_input_credits_per_1m))


def _output_credits_per_1m() -> Decimal:
    return Decimal(str(get_settings().kie_output_credits_per_1m))


def estimate_tokens(text: str) -> int:
    """Оценка токенов для кириллицы: ~3 символа на токен."""
    if not text:
        return 0
    return max(1, len(text) // 3)


def estimate_messages_tokens(messages: list[dict]) -> int:
    total = 0
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total += estimate_tokens(part.get("text", ""))
        elif isinstance(content, str):
            total += estimate_tokens(content)
    return max(total, 1)


def total_tokens(input_tokens: int, output_tokens: int) -> int:
    return max(input_tokens, 0) + max(output_tokens, 0)


def merge_api_usage(*usages: dict[str, int] | None) -> dict[str, int] | None:
    input_tokens = 0
    output_tokens = 0
    for usage in usages:
        if not usage:
            continue
        input_tokens += max(int(usage.get("input_tokens", 0)), 0)
        output_tokens += max(int(usage.get("output_tokens", 0)), 0)
    if input_tokens == 0 and output_tokens == 0:
        return None
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}


def provider_cost_credits(input_tokens: int, output_tokens: int) -> Decimal:
    input_cr = Decimal(input_tokens) / Decimal(1_000_000) * _input_credits_per_1m()
    output_cr = Decimal(output_tokens) / Decimal(1_000_000) * _output_credits_per_1m()
    return (input_cr + output_cr).quantize(Decimal("0.0001"))


def provider_cost_usd(input_tokens: int, output_tokens: int) -> Decimal:
    """Реальная себестоимость KIE: credits × $0.005."""
    credits = provider_cost_credits(input_tokens, output_tokens)
    return (credits * _kie_credit_usd()).quantize(Decimal("0.0000001"))


def provider_cost_rub(input_tokens: int, output_tokens: int) -> Decimal:
    return (provider_cost_usd(input_tokens, output_tokens) * USD_TO_RUB).quantize(Decimal("0.0001"))


def charge_usd_from_credits(credits: Decimal) -> Decimal:
    """Списание в $: (credits × $0.007) × markup."""
    return (credits * _billing_credit_usd() * _charge_markup()).quantize(Decimal("0.0000001"))


def charge_rub_from_credits(credits: Decimal) -> Decimal:
    return (charge_usd_from_credits(credits) * USD_TO_RUB).quantize(Decimal("0.01"))


def charge_rub(input_tokens: int, output_tokens: int) -> Decimal:
    return charge_rub_from_credits(provider_cost_credits(input_tokens, output_tokens))


def display_provider_cost_usd(cost_usd: Decimal) -> Decimal:
    """Себестоимость для админ-дашборда (коррекция расхождения с KIE)."""
    multiplier = Decimal(str(get_settings().provider_cost_display_multiplier))
    return (cost_usd * multiplier).quantize(Decimal("0.0000001"))


def display_provider_cost_rub(cost_usd: Decimal) -> Decimal:
    return (display_provider_cost_usd(cost_usd) * USD_TO_RUB).quantize(Decimal("0.01"))


def image_generation_provider_cost_usd() -> Decimal:
    return Decimal(str(get_settings().image_generation_provider_cost_usd))


def image_generation_charge_rub() -> Decimal:
    cost_usd = image_generation_provider_cost_usd()
    markup = Decimal(str(get_settings().image_generation_markup))
    return (cost_usd * markup * USD_TO_RUB).quantize(Decimal("0.01"))


VISION_INFOGRAPHIC_CHARGE_RUB = Decimal("100")


def vision_infographic_charge_rub(mode: str | None = None) -> Decimal:
    if mode in {"aura", "palm"}:
        return VISION_INFOGRAPHIC_CHARGE_RUB
    return image_generation_charge_rub()


def format_balance(amount: Decimal | None) -> str:
    value = Decimal(amount or 0).quantize(Decimal("0.01"))
    if value == value.to_integral_value():
        return f"{int(value)} ₽"
    return f"{value} ₽"
