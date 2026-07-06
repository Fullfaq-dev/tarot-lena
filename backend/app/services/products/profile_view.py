"""Формирование текста профиля пользователя для бота Лея."""

from __future__ import annotations

from sqlalchemy import select

from app.database.models import ProductUsage, SoulProfile, User, UserSettings
from app.database.session import AsyncSessionLocal
from app.services.astrology.zodiac import zodiac_sign
from app.services.numerology.calculations import life_path_number
from app.services.products.catalog import PRODUCTS
from app.services.products.entitlements import EntitlementService


def _fmt(value: str | None) -> str:
    return value.strip() if value and str(value).strip() else "—"


async def build_leia_profile_text(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return "Сначала нажми /start"

        profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
        settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))

        lines = ["👤 **Твой профиль**\n"]

        if profile:
            lines.append(f"**Имя:** {_fmt(profile.name)}")
            if profile.birth_date:
                bd = profile.birth_date.strftime("%d.%m.%Y")
                sign, emoji = zodiac_sign(profile.birth_date)
                lp = life_path_number(profile.birth_date)
                lines.append(f"**Дата рождения:** {bd}")
                lines.append(f"**Знак зодиака:** {sign} {emoji}")
                lines.append(f"**Число пути:** {lp}")
            else:
                lines.append("**Дата рождения:** —")
            lines.append(f"**Время рождения:** {_fmt(profile.birth_time)}")
            lines.append(f"**Место рождения:** {_fmt(profile.birth_city)}")

            prefs = profile.preferences or {}
            partner = prefs.get("partner_birth_date")
            if partner:
                lines.append(f"**Партнёр (ДР):** {partner}")
        else:
            lines.append("_Анкета не заполнена — /start_")

        plan = await EntitlementService().active_plan_label(user.id)
        lines.append("")
        lines.append(f"**Пакет:** {plan or 'нет активного'}")

        usages = await session.execute(
            select(ProductUsage).where(ProductUsage.user_id == user.id)
        )
        usage_rows = list(usages.scalars().all())
        mini_done = {u.product_id for u in usage_rows if u.level == "mini"}
        full_count: dict[str, int] = {}
        for u in usage_rows:
            if u.level == "full":
                full_count[u.product_id] = full_count.get(u.product_id, 0) + 1

        lines.append("")
        lines.append("**Разборы:**")
        for product in PRODUCTS.values():
            parts = []
            if product.id in mini_done:
                parts.append("мини ✓")
            n_full = full_count.get(product.id, 0)
            if n_full:
                parts.append(f"полных: {n_full}")
            status = ", ".join(parts) if parts else "ещё не было"
            lines.append(f"{product.emoji} {product.title} — {status}")

        lines.append("")
        if settings:
            lines.append(f"**Часовой пояс:** {settings.timezone}")
        if user.username:
            lines.append(f"**Telegram:** @{user.username}")
        lines.append(f"**ID:** `{user.telegram_id}`")
        if user.created_at:
            lines.append(
                f"**С нами с:** {user.created_at.strftime('%d.%m.%Y')}"
            )

        return "\n".join(lines)
