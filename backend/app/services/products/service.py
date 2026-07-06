import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Payment, ProductUsage, SoulProfile, User
from app.database.session import AsyncSessionLocal
from app.services.ai.kie_client import KieClient
from app.services.astrology.zodiac import zodiac_sign
from app.services.numerology.calculations import life_path_number, personal_year_number
from app.services.products.catalog import PRODUCTS, product_purpose
from app.services.products.entitlements import EntitlementService
from app.services.products.prompts import astro_system, numerology_system
from app.services.billing.providers import PaymentFlowResult

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self) -> None:
        self.kie = KieClient()

    async def _profile(self, session: AsyncSession, user_id: str) -> SoulProfile | None:
        return await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user_id))

    async def has_mini(self, user_id: str, product_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage.id).where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.product_id == product_id,
                    ProductUsage.level == "mini",
                )
            )
            return row is not None

    async def has_full_access(self, user_id: str, product_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage.id).where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.product_id == product_id,
                    ProductUsage.level == "full",
                )
            )
            return row is not None

    async def is_full_blocked(self, user_id: str, product_id: str) -> bool:
        if await EntitlementService().can_use_full_free(user_id, product_id):
            return False
        return await self.has_full_access(user_id, product_id)

    async def record_usage(
        self,
        session: AsyncSession,
        user_id: str,
        product_id: str,
        level: str,
        *,
        payment_id: str | None = None,
        content: str = "",
    ) -> None:
        session.add(
            ProductUsage(
                user_id=user_id,
                product_id=product_id,
                level=level,
                payment_id=payment_id,
                content_preview=content[:500] if content else None,
            )
        )

    async def create_full_payment(
        self, user: User, product_id: str, *, extra_context: str = ""
    ) -> PaymentFlowResult:
        from app.services.billing.service import BillingService

        product = PRODUCTS.get(product_id)
        if product is None:
            raise ValueError("Неизвестный продукт")
        extra_payload = {"extra_context": extra_context} if extra_context else None
        async with AsyncSessionLocal() as session:
            db_user = await session.scalar(select(User).where(User.id == user.id))
            if db_user is None:
                raise ValueError("Пользователь не найден")
            return await BillingService()._initiate_platega_payment(
                session,
                db_user,
                product.price_rub,
                product_purpose(product_id),
                extra_payload=extra_payload,
            )

    async def create_package_payment(self, user: User, package_id: str) -> PaymentFlowResult:
        from app.services.billing.service import BillingService
        from app.services.products.packages import PACKAGES

        package = PACKAGES.get(package_id)
        if package is None:
            raise ValueError("Неизвестный пакет")
        async with AsyncSessionLocal() as session:
            db_user = await session.scalar(select(User).where(User.id == user.id))
            if db_user is None:
                raise ValueError("Пользователь не найден")
            return await BillingService()._initiate_platega_payment(
                session,
                db_user,
                package.price_rub,
                package.purpose,
            )

    async def generate_portrait(self, user_id: str) -> str:
        async with AsyncSessionLocal() as session:
            profile = await self._profile(session, user_id)
            if profile is None or profile.birth_date is None:
                return "Для портрета нужна дата рождения. Нажми /start и заполни анкету."

            name = profile.name or "друг"
            lp = life_path_number(profile.birth_date)
            py = personal_year_number(profile.birth_date)
            sign, emoji = zodiac_sign(profile.birth_date)
            year = date.today().year

            user_prompt = (
                f"Составь нумерологический портрет для {name}.\n"
                f"Дата рождения: {profile.birth_date.strftime('%d.%m.%Y')}\n"
                f"Место: {profile.birth_city or 'не указано'}\n"
                f"Число жизненного пути: {lp}\n"
                f"Личное число года {year}: {py}\n"
                f"Знак зодиака: {sign} {emoji}\n\n"
                "Формат как в примере: заголовок, число пути, сила, точка роста, "
                f"задача на {year}, аркан-покровитель, совет от Леи. "
                "В конце: «💎 Хочешь узнать больше о какой-то из сфер жизни?»"
            )
            messages = [
                {"role": "system", "content": [{"type": "text", "text": numerology_system()}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ]
            return await self.kie.chat_completion(messages)

    async def generate_mini(
        self,
        user_id: str,
        product_id: str,
        *,
        extra_context: str = "",
    ) -> str:
        product = PRODUCTS[product_id]
        async with AsyncSessionLocal() as session:
            profile = await self._profile(session, user_id)
            if profile is None:
                return "Сначала пройди анкету — /start"

            name = profile.name or "ты"
            bd = profile.birth_date.strftime("%d.%m.%Y") if profile.birth_date else "—"
            sign, emoji = zodiac_sign(profile.birth_date) if profile.birth_date else ("—", "")

            prompts = {
                "love": (
                    f"Мини-разбор отношений для {name} (ДР: {bd}).\n"
                    f"Партнёр: {extra_context}\n"
                    "Формат: 🧠 МЫСЛИ, ❤️ ЧУВСТВА, 🎯 ДЕЙСТВИЯ (кратко). "
                    "В конце: «💎 Хотите полную расшифровку?»"
                ),
                "wealth": (
                    f"Мини денежный код для {name}, ДР {bd}. "
                    "Число богатства + 1 совет + куда утекают деньги. Кратко."
                ),
                "negative": (
                    f"Мини энергодиагностика для {name}, ДР {bd}. "
                    "Индекс чистоты 0-10 + одна сфера внимания. Кратко."
                ),
                "forecast": (
                    f"Мини-прогноз на неделю для {name}, знак {sign} {emoji}, ДР {bd}. "
                    "Любовь, деньги, здоровье — по 1 предложению."
                ),
                "question": (
                    f"Мини-ответ Леи для {name} (ДР {bd}, {sign}):\n"
                    f"Вопрос: {extra_context}\n"
                    "Краткий ответ таро+нумерология, 4-6 предложений."
                ),
            }
            user_prompt = prompts.get(product_id, product.mini_hint)
            messages = [
                {"role": "system", "content": [{"type": "text", "text": numerology_system()}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ]
            text = await self.kie.chat_completion(messages)
            await self.record_usage(session, user_id, product_id, "mini", content=text)
            await session.commit()
            return text

    async def generate_full(
        self,
        user_id: str,
        product_id: str,
        *,
        extra_context: str = "",
        payment_id: str | None = None,
        use_entitlement: bool = False,
    ) -> str:
        async with AsyncSessionLocal() as session:
            profile = await self._profile(session, user_id)
            if profile is None:
                return "Сначала пройди анкету — /start"

            name = profile.name or "ты"
            bd = profile.birth_date.strftime("%d.%m.%Y") if profile.birth_date else "—"
            sign, emoji = zodiac_sign(profile.birth_date) if profile.birth_date else ("—", "")

            full_prompts = {
                "love": (
                    f"ПОЛНЫЙ разбор отношений для {name} (ДР: {bd}). Партнёр: {extra_context}. "
                    "Совместимость по нумерологии, кармический аркан пары, астрология, "
                    "мысли/чувства/действия партнёра, подводные камни, совет."
                ),
                "wealth": (
                    f"ПОЛНЫЙ нумерологический расчёт богатства для {name}, ДР {bd}. "
                    "Число богатства, чёрные дыры, топ-3 профессии, даты на 3 месяца, аффирмация."
                ),
                "negative": (
                    f"ПОЛНАЯ диагностика негатива для {name}, ДР {bd}. "
                    "5 сфер, блоки, индекс чистоты, ритуал/практика, аркан-защитник."
                ),
                "forecast": (
                    f"ПОЛНЫЙ прогноз на месяц для {name}, {sign} {emoji}, ДР {bd}. "
                    "4 недели, даты, аркан месяца, астросоветы."
                ),
                "question": (
                    f"ПОЛНЫЙ ответ для {name} (ДР {bd}): {extra_context}. "
                    "Таро + нумерология, развёрнуто, с конкретными шагами."
                ),
            }
            user_prompt = full_prompts.get(product_id, extra_context)
            messages = [
                {"role": "system", "content": [{"type": "text", "text": numerology_system()}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ]
            text = await self.kie.chat_completion(messages)
            await self.record_usage(
                session, user_id, product_id, "full", payment_id=payment_id, content=text
            )
            if use_entitlement:
                await EntitlementService().consume_credit(session, user_id, product_id)
            await session.commit()
            return text

    async def fulfill_payment(self, session: AsyncSession, payment: Payment) -> str | None:
        purpose = payment.purpose
        if not purpose.startswith("product_") or not purpose.endswith("_full"):
            return None
        product_id = purpose.removeprefix("product_").removesuffix("_full")
        if product_id not in PRODUCTS:
            return None
        prefs = (payment.payload or {}).get("extra_context", "")
        if product_id in ("love", "question") and not prefs:
            payload = dict(payment.payload or {})
            payload["awaiting_context"] = True
            payment.payload = payload
            await session.flush()
            return None
        return await self._generate_full_in_session(
            session,
            payment.user_id,
            product_id,
            extra_context=prefs,
            payment_id=payment.id,
        )

    async def _generate_full_in_session(
        self,
        session: AsyncSession,
        user_id: str,
        product_id: str,
        *,
        extra_context: str = "",
        payment_id: str | None = None,
        use_entitlement: bool = False,
    ) -> str:
        profile = await self._profile(session, user_id)
        if profile is None:
            return "Сначала пройди анкету — /start"

        name = profile.name or "ты"
        bd = profile.birth_date.strftime("%d.%m.%Y") if profile.birth_date else "—"
        sign, emoji = zodiac_sign(profile.birth_date) if profile.birth_date else ("—", "")

        full_prompts = {
            "love": (
                f"ПОЛНЫЙ разбор отношений для {name} (ДР: {bd}). Партнёр: {extra_context}. "
                "Совместимость по нумерологии, кармический аркан пары, астрология, "
                "мысли/чувства/действия партнёра, подводные камни, совет."
            ),
            "wealth": (
                f"ПОЛНЫЙ нумерологический расчёт богатства для {name}, ДР {bd}. "
                "Число богатства, чёрные дыры, топ-3 профессии, даты на 3 месяца, аффирмация."
            ),
            "negative": (
                f"ПОЛНАЯ диагностика негатива для {name}, ДР {bd}. "
                "5 сфер, блоки, индекс чистоты, ритуал/практика, аркан-защитник."
            ),
            "forecast": (
                f"ПОЛНЫЙ прогноз на месяц для {name}, {sign} {emoji}, ДР {bd}. "
                "4 недели, даты, аркан месяца, астросоветы."
            ),
            "question": (
                f"ПОЛНЫЙ ответ для {name} (ДР {bd}): {extra_context}. "
                "Таро + нумерология, развёрнуто, с конкретными шагами."
            ),
        }
        user_prompt = full_prompts.get(product_id, extra_context)
        messages = [
            {"role": "system", "content": [{"type": "text", "text": numerology_system()}]},
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ]
        text = await self.kie.chat_completion(messages)
        await self.record_usage(
            session, user_id, product_id, "full", payment_id=payment_id, content=text
        )
        if use_entitlement:
            await EntitlementService().consume_credit(session, user_id, product_id)
        return text
