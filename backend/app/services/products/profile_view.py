"""Формирование текста профиля пользователя для бота Лея."""

from __future__ import annotations

from sqlalchemy import select

from app.bot.leia_rich import format_leia_profile_rich
from app.database.models import ProductUsage, SoulProfile, User, UserSettings
from app.database.session import AsyncSessionLocal
from app.services.astrology.zodiac import zodiac_sign
from app.services.numerology.calculations import life_path_number
from app.services.products.catalog import PRODUCTS
from app.services.products.entitlements import EntitlementService


def _fmt(value: str | None) -> str:
    return value.strip() if value and str(value).strip() else "—"


def _usage_label(product_id: str, *, mini_done: bool, full_count: int) -> str:
    if full_count and mini_done:
        return f"мини ✓ · полных: {full_count}"
    if full_count:
        return f"полных: {full_count}"
    if mini_done:
        return "мини ✓"
    return "ещё не пробовала"


async def build_leia_profile_text(telegram_id: int) -> str:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return "Сначала нажми /start"

        profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
        settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))

        name = _fmt(profile.name if profile else None)
        birth_date = "—"
        zodiac = "—"
        life_path = "—"
        birth_time = _fmt(profile.birth_time if profile else None)
        birth_city = _fmt(profile.birth_city if profile else None)
        partner_birth = None

        if profile and profile.birth_date:
            birth_date = profile.birth_date.strftime("%d.%m.%Y")
            sign, emoji = zodiac_sign(profile.birth_date)
            zodiac = f"{sign} {emoji}"
            life_path = str(life_path_number(profile.birth_date))
            prefs = profile.preferences or {}
            partner = prefs.get("partner_birth_date")
            if partner:
                partner_birth = str(partner)

        plan = await EntitlementService().active_plan_label(user.id)

        usages = await session.execute(
            select(ProductUsage).where(ProductUsage.user_id == user.id)
        )
        usage_rows = list(usages.scalars().all())
        mini_done = {u.product_id for u in usage_rows if u.level == "mini"}
        full_count: dict[str, int] = {}
        for u in usage_rows:
            if u.level == "full":
                full_count[u.product_id] = full_count.get(u.product_id, 0) + 1

        product_rows = [
            [
                f"{product.emoji} {product.title}",
                _usage_label(product.id, mini_done=product.id in mini_done, full_count=full_count.get(product.id, 0)),
            ]
            for product in PRODUCTS.values()
        ]

        return format_leia_profile_rich(
            name=name,
            birth_date=birth_date,
            zodiac=zodiac,
            life_path=life_path,
            birth_time=birth_time,
            birth_city=birth_city,
            partner_birth=partner_birth,
            plan_label=plan,
            product_rows=product_rows,
            timezone=settings.timezone if settings else "Europe/Moscow",
            username=user.username,
            telegram_id=user.telegram_id,
            member_since=user.created_at.strftime("%d.%m.%Y") if user.created_at else "—",
            has_profile=bool(profile and profile.birth_date),
        )
