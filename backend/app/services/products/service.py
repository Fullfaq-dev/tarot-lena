import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Payment, ProductUsage, SoulProfile, User
from app.database.session import AsyncSessionLocal
from app.bot.leia_rich import enrich_ai_prompt, normalize_leia_rich
from app.services.ai.kie_client import KieClient
from app.services.astrology.zodiac import zodiac_sign
from app.services.numerology.calculations import life_path_number, personal_year_number
from app.services.products.catalog import PRODUCTS, product_purpose
from app.services.products.entitlements import EntitlementService
from app.services.numerology.service import NumerologyService
from app.services.products.prompts import leia_reading_system
from app.services.billing.providers import PaymentFlowResult
from app.services.tarot.service import TarotService

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
                content_preview=content[:4000] if content else None,
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

    async def _complete_leia(self, messages: list) -> str:
        text = await self.kie.chat_completion(messages)
        return normalize_leia_rich(text)

    async def latest_full_reading(self, user_id: str) -> str:
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage)
                .where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.level == "full",
                )
                .order_by(ProductUsage.created_at.desc())
            )
            return (row.content_preview or "") if row else ""

    async def latest_reading_context(self, user_id: str) -> str:
        """Last non-empty reading text for follow-up chat (full preferred)."""
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage)
                .where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
                .order_by(ProductUsage.created_at.desc())
            )
            if row and row.content_preview:
                return row.content_preview
            return ""

    async def generate_tarot_spread(
        self,
        user_id: str,
        question: str,
        *,
        level: str = "mini",
        payment_id: str | None = None,
        use_entitlement: bool = False,
    ) -> tuple[str, list[dict]]:
        async with AsyncSessionLocal() as session:
            profile = await self._profile(session, user_id)
            if profile is None:
                return "Сначала пройди анкету — /start", []

            name = profile.name or "ты"
            bd = profile.birth_date.strftime("%d.%m.%Y") if profile.birth_date else "—"
            cards = TarotService().draw_cards(4)
            card_block = "\n".join(
                f"{idx + 1}. {card['name']} — {card.get('description', '')}"
                for idx, card in enumerate(cards)
            )
            depth = "полный" if level == "full" else "мини"
            user_prompt = enrich_ai_prompt(
                f"{depth.capitalize()} расклад Таро (4 карты) для {name}, ДР {bd}.\n"
                f"Вопрос: {question}\n\n"
                f"Выпавшие карты:\n{card_block}\n\n"
                "Дай толкование по каждой позиции (1–4), общий вывод и совет от Леи. "
                "Заголовок ### 🃏 Расклад Таро."
            )
            if level == "mini":
                user_prompt = enrich_ai_prompt(
                    f"Мини-расклад Таро (4 карты) для {name}.\n"
                    f"Вопрос: {question}\n\n"
                    f"Карты:\n{card_block}\n\n"
                    "Кратко: 1–2 предложения на карту + итог. "
                    "В конце: «💎 Хочешь полную расшифровку?»"
                )
            messages = [
                {"role": "system", "content": [{"type": "text", "text": leia_reading_system()}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ]
            text = await self._complete_leia(messages)
            await self.record_usage(
                session,
                user_id,
                "tarot_spread",
                level,
                payment_id=payment_id,
                content=text,
            )
            if use_entitlement and level == "full":
                await EntitlementService().consume_credit(session, user_id, "tarot_spread")
            await session.commit()
            return text, cards

    async def generate_mini_portrait(self, user_id: str) -> str:
        async with AsyncSessionLocal() as session:
            profile = await self._profile(session, user_id)
            if profile is None or profile.birth_date is None:
                return "Для портрета нужна дата рождения. Нажми /start и заполни анкету."

            name = profile.name or "дорогая"
            ctx = NumerologyService().profile_context(
                name=name,
                birth=profile.birth_date,
                birth_city=profile.birth_city,
            )
            user_prompt = enrich_ai_prompt(
                f"Составь МИНИ **Матрицу судьбы** (метод Хшановской) для {name}.\n\n{ctx}\n\n"
                "Формат: ### 🔮 Твоя матрица судьбы, таблица ключевых чисел матрицы, "
                "архетип, одна сила, одна точка роста, аркан-покровитель, совет от Леи. "
                "Кратко — не больше 8–10 предложений."
            )
            messages = [
                {"role": "system", "content": [{"type": "text", "text": leia_reading_system()}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ]
            return await self._complete_leia(messages)

    async def generate_portrait(self, user_id: str) -> str:
        return await self.generate_mini_portrait(user_id)

    async def generate_portrait_full(self, user_id: str) -> str:
        async with AsyncSessionLocal() as session:
            profile = await self._profile(session, user_id)
            if profile is None or profile.birth_date is None:
                return "Для портрета нужна дата рождения. Нажми /start и заполни анкету."

            name = profile.name or "друг"
            ctx = NumerologyService().profile_context(
                name=name,
                birth=profile.birth_date,
                birth_city=profile.birth_city,
            )
            year = date.today().year

            user_prompt = enrich_ai_prompt(
                f"Составь полную **Матрицу судьбы** (метод Хшановской) для {name}.\n\n{ctx}\n\n"
                "Структура: заголовок ###, таблица матрицы и ключевых чисел, "
                "сильные стороны, зоны роста, кармические задачи, "
                f"фокус на {year}, аркан-покровитель, совет от Леи. "
                "В конце: «💎 Хочешь узнать больше о какой-то из сфер жизни?»"
            )
            messages = [
                {"role": "system", "content": [{"type": "text", "text": leia_reading_system()}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ]
            return await self._complete_leia(messages)

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
                "love": enrich_ai_prompt(
                    f"Мини-разбор отношений для {name} (ДР: {bd}).\n"
                    f"Партнёр: {extra_context}\n"
                    "Секции: 🧠 Мысли, ❤️ Чувства, 🎯 Действия — кратко. "
                    "В конце: «💎 Хочешь полную расшифровку?»"
                ),
                "wealth": enrich_ai_prompt(
                    f"Мини денежный код для {name}, ДР {bd}. "
                    "Число богатства + 1 совет + куда утекают деньги. Кратко."
                ),
                "negative": enrich_ai_prompt(
                    f"Мини энергодиагностика для {name}, ДР {bd}. "
                    "Индекс чистоты 0–10 + одна сфера внимания. Кратко."
                ),
                "forecast": enrich_ai_prompt(
                    f"Мини-матрица судьбы (Хшановская) для {name}, ДР {bd}.\n"
                    f"{NumerologyService().profile_context(name=name, birth=profile.birth_date, birth_city=profile.birth_city) if profile.birth_date else ''}\n"
                    "Ключевые энергии матрицы + 1 сила + 1 точка роста. Кратко."
                ),
                "question": enrich_ai_prompt(
                    f"Мини-ответ Леи для {name} (ДР {bd}, {sign}):\n"
                    f"Вопрос: {extra_context}\n"
                    "Краткий ответ таро+нумерология, 4–6 предложений."
                ),
            }
            user_prompt = prompts.get(product_id, enrich_ai_prompt(product.mini_hint))
            messages = [
                {"role": "system", "content": [{"type": "text", "text": leia_reading_system()}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ]
            text = await self._complete_leia(messages)
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
                "love": enrich_ai_prompt(
                    f"Полный разбор отношений для {name} (ДР: {bd}). Партнёр: {extra_context}. "
                    "Совместимость, кармический аркан пары, астрология, "
                    "мысли/чувства/действия партнёра, подводные камни, совет."
                ),
                "wealth": enrich_ai_prompt(
                    f"Полный нумерологический расчёт богатства для {name}, ДР {bd}. "
                    "Число богатства, чёрные дыры, топ-3 профессии, даты на 3 месяца, аффирмация."
                ),
                "negative": enrich_ai_prompt(
                    f"Полная диагностика негатива для {name}, ДР {bd}. "
                    "5 сфер, блоки, индекс чистоты, ритуал/практика, аркан-защитник."
                ),
                "forecast": enrich_ai_prompt(
                    f"Полная **Матрица судьбы** (Хшановская) для {name}, ДР {bd}.\n"
                    f"{NumerologyService().profile_context(name=name, birth=profile.birth_date, birth_city=profile.birth_city) if profile.birth_date else ''}\n"
                    "Разбор ключевых энергий матрицы, кармические задачи, "
                    "сильные стороны, зоны роста, персональные рекомендации."
                ),
                "question": enrich_ai_prompt(
                    f"Полный ответ для {name} (ДР {bd}): {extra_context}. "
                    "Таро + нумерология, развёрнуто, с конкретными шагами."
                ),
            }
            user_prompt = full_prompts.get(product_id, enrich_ai_prompt(extra_context))
            messages = [
                {"role": "system", "content": [{"type": "text", "text": leia_reading_system()}]},
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
            ]
            text = await self._complete_leia(messages)
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
        if product_id in ("love", "question", "tarot_spread") and not prefs:
            payload = dict(payment.payload or {})
            payload["awaiting_context"] = True
            payment.payload = payload
            await session.flush()
            return None
        if product_id == "tarot_spread":
            text, cards = await self.generate_tarot_spread(
                payment.user_id,
                prefs,
                level="full",
                payment_id=payment.id,
            )
            payload = dict(payment.payload or {})
            payload["tarot_card_slugs"] = [str(c.get("slug", "")) for c in cards]
            payload["tarot_question"] = prefs
            payment.payload = payload
            return text
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
            "love": enrich_ai_prompt(
                f"Полный разбор отношений для {name} (ДР: {bd}). Партнёр: {extra_context}. "
                "Совместимость, кармический аркан пары, астрология, "
                "мысли/чувства/действия партнёра, подводные камни, совет."
            ),
            "wealth": enrich_ai_prompt(
                f"Полный нумерологический расчёт богатства для {name}, ДР {bd}. "
                "Число богатства, чёрные дыры, топ-3 профессии, даты на 3 месяца, аффирмация."
            ),
            "negative": enrich_ai_prompt(
                f"Полная диагностика негатива для {name}, ДР {bd}. "
                "5 сфер, блоки, индекс чистоты, ритуал/практика, аркан-защитник."
            ),
            "forecast": enrich_ai_prompt(
                f"Полная **Матрица судьбы** (Хшановская) для {name}, ДР {bd}.\n"
                f"{NumerologyService().profile_context(name=name, birth=profile.birth_date, birth_city=profile.birth_city) if profile.birth_date else ''}\n"
                "Разбор ключевых энергий матрицы, кармические задачи, "
                "сильные стороны, зоны роста, персональные рекомендации."
            ),
            "question": enrich_ai_prompt(
                f"Полный ответ для {name} (ДР {bd}): {extra_context}. "
                "Таро + нумерология, развёрнуто, с конкретными шагами."
            ),
        }
        user_prompt = full_prompts.get(product_id, enrich_ai_prompt(extra_context))
        messages = [
            {"role": "system", "content": [{"type": "text", "text": leia_reading_system()}]},
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ]
        text = await self._complete_leia(messages)
        await self.record_usage(
            session, user_id, product_id, "full", payment_id=payment_id, content=text
        )
        if use_entitlement:
            await EntitlementService().consume_credit(session, user_id, product_id)
        return text
