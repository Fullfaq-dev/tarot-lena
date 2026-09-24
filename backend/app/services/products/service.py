import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Message, MessageRole, Payment, ProductUsage, SoulProfile, User
from app.database.session import AsyncSessionLocal
from app.bot.leia_rich import normalize_leia_rich
from app.services.ai.kie_client import KieClient
from app.services.numerology.service import NumerologyService
from app.services.products.catalog import PRODUCTS, product_purpose
from app.services.products.entitlements import EntitlementService
from app.services.products.prompts import (
    product_system,
    user_trigger,
)
from app.services.billing.providers import PaymentFlowResult
from app.services.tarot.service import TarotService

logger = logging.getLogger(__name__)


class ProductService:
    def __init__(self) -> None:
        self.kie = KieClient()

    async def _profile(self, session: AsyncSession, user_id: str) -> SoulProfile | None:
        return await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user_id))

    async def has_mini(self, user_id: str, product_id: str) -> bool:
        """True only if a successful mini (with text) was already delivered."""
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage.id).where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.product_id == product_id,
                    ProductUsage.level == "mini",
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
            )
            return row is not None

    async def has_full_access(self, user_id: str, product_id: str) -> bool:
        """True only if a successful full reading (with text) was already delivered."""
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage.id).where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.product_id == product_id,
                    ProductUsage.level == "full",
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
            )
            return row is not None

    async def latest_full_for_product(self, user_id: str, product_id: str) -> str:
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage)
                .where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.product_id == product_id,
                    ProductUsage.level == "full",
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
                .order_by(ProductUsage.created_at.desc())
            )
            return (row.content_preview or "") if row else ""

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
        usage = ProductUsage(
            user_id=user_id,
            product_id=product_id,
            level=level,
            payment_id=payment_id,
            content_preview=content[:4000] if content else None,
        )
        session.add(usage)
        if content.strip():
            await session.flush()
            product = PRODUCTS.get(product_id)
            title = f"{product.emoji} {product.title}" if product else product_id
            level_label = "мини" if level == "mini" else "полная"
            session.add(
                Message(
                    user_id=user_id,
                    role=MessageRole.ASSISTANT.value,
                    content=content[:20000],
                    meta={
                        "source": "product_reading",
                        "product_id": product_id,
                        "product_title": title,
                        "level": level,
                        "level_label": level_label,
                        "product_usage_id": usage.id,
                        "payment_id": payment_id,
                    },
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

    async def _complete_leia(
        self,
        messages: list,
        *,
        user_id: str | None = None,
        feature: str = "leia_product",
        question: str = "",
    ) -> str:
        """One retry only on transport errors — empty answers fail fast to fallbacks."""
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                text = normalize_leia_rich(await self.kie.chat_completion(messages))
                text = text.strip() and text or ""
                if text and user_id:
                    from app.services.billing.usage_log import record_kie_usage

                    await record_kie_usage(
                        user_id,
                        feature=feature,
                        question=question,
                        answer=text,
                        api_usage=self.kie.last_usage,
                    )
                return text
            except Exception as exc:
                last_error = exc
                logger.warning("Leia AI attempt %s failed: %s", attempt + 1, exc)
        if last_error:
            logger.error("Leia AI failed after retries: %s", last_error)
        return ""

    @staticmethod
    def _tarot_fallback_text(question: str, cards: list[dict], *, level: str) -> str:
        """Narrative fallback when AI is down — not a second card table."""
        lines = [
            "### ✨ Что говорят карты",
            "",
            f"По вопросу «{question}» вижу такой акцент:",
            "",
        ]
        for idx, card in enumerate(cards, 1):
            name = str(card.get("name", "Карта"))
            desc = str(card.get("description", "важное послание"))
            lines.append(f"**Позиция {idx} — {name}.** {desc.capitalize()}.")
        lines.append("")
        names = ", ".join(str(c.get("name", "карта")) for c in cards)
        lines.append(
            f"Вместе карты ({names}) намекают: смотри на ситуацию шире — "
            "есть и опора, и место для осознанного шага."
        )
        lines.append("")
        if level == "mini":
            lines.append("💎 Хочешь полную расшифровку с советом по каждой позиции?")
        else:
            lines.append("Могу уточнить любую позицию — просто напиши вопрос.")
        return normalize_leia_rich("\n".join(lines))

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

    async def history_page(
        self, user_id: str, page: int = 0, *, page_size: int = 5
    ) -> tuple[list[ProductUsage], int, int]:
        from sqlalchemy import func

        page = max(0, page)
        async with AsyncSessionLocal() as session:
            total = await session.scalar(
                select(func.count())
                .select_from(ProductUsage)
                .where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
            ) or 0
            total_pages = max(1, (total + page_size - 1) // page_size)
            if page >= total_pages:
                page = total_pages - 1
            rows = await session.scalars(
                select(ProductUsage)
                .where(
                    ProductUsage.user_id == user_id,
                    ProductUsage.content_preview.isnot(None),
                    ProductUsage.content_preview != "",
                )
                .order_by(ProductUsage.created_at.desc())
                .offset(page * page_size)
                .limit(page_size)
            )
            return list(rows.all()), page, total_pages

    async def get_usage(self, user_id: str, usage_id: str) -> ProductUsage | None:
        async with AsyncSessionLocal() as session:
            row = await session.scalar(
                select(ProductUsage).where(
                    ProductUsage.id == usage_id,
                    ProductUsage.user_id == user_id,
                )
            )
            if row is None:
                return None
            # Detach fields we need outside the session.
            session.expunge(row)
            return row

    def _prompt_vars(
        self,
        profile: SoulProfile,
        *,
        partner_bd: str = "",
        question: str = "",
        cards: str = "",
        chat_text: str = "",
        chat_role: str = "",
    ) -> dict[str, str | int]:
        return NumerologyService().prompt_vars(
            name=profile.name or "ты",
            birth=profile.birth_date,
            birth_city=profile.birth_city,
            partner_bd=partner_bd,
            question=question,
            cards=cards,
            chat_text=chat_text,
            chat_role=chat_role,
        )

    @staticmethod
    def pack_chat_context(*, text: str, image_urls: list[str] | None = None) -> str:
        """Упаковка переписки для payment/generate. Роль не передаём — модель сама читает подписи."""
        urls = [u.strip() for u in (image_urls or []) if u and str(u).strip()]
        parts: list[str] = []
        if urls:
            parts.append("<<<IMAGES>>>\n" + "\n".join(urls[:12]))
        parts.append("<<<CHAT>>>\n" + (text or "").strip())
        return "\n".join(parts)

    @staticmethod
    def _parse_chat_extra(extra: str) -> tuple[str, list[str]]:
        """Returns (chat_text, image_urls). Legacy chat_role= в head игнорируется."""
        raw = (extra or "").strip()
        images: list[str] = []
        body = raw
        if "<<<IMAGES>>>" in raw:
            _before, rest = raw.split("<<<IMAGES>>>", 1)
            if "<<<CHAT>>>" in rest:
                img_block, body = rest.split("<<<CHAT>>>", 1)
            else:
                img_block, body = rest, ""
            for line in img_block.splitlines():
                line = line.strip()
                if line.startswith("http") or line.startswith("data:image"):
                    images.append(line)
                elif line.startswith("images="):
                    images.extend(
                        u.strip() for u in line.split("=", 1)[1].split(",") if u.strip().startswith("http")
                    )
        elif "<<<CHAT>>>" in raw:
            _head, body = raw.split("<<<CHAT>>>", 1)
        text = body.strip()
        if not text and images:
            text = "(переписка на скриншотах — см. изображения в запросе)"
        return text, images

    @staticmethod
    def _chat_user_content(trigger: str, image_urls: list[str]) -> list[dict]:
        parts: list[dict] = [{"type": "text", "text": trigger}]
        for url in image_urls[:12]:
            parts.append({"type": "image_url", "image_url": {"url": url}})
        return parts

    @staticmethod
    def _format_cards(cards: list[dict], *, positions: list[str] | None = None) -> str:
        lines = []
        for idx, card in enumerate(cards):
            label = positions[idx] if positions and idx < len(positions) else str(idx + 1)
            lines.append(f"{label}: {card['name']} — {card.get('description', '')}")
        return "\n".join(lines)

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

            cards = TarotService().draw_cards(4)
            positions = ["ситуация", "что мешает", "что помогает", "итог"]
            if level == "mini":
                # Мини: только позиция «что мешает»
                card_block = self._format_cards([cards[1]], positions=["что мешает"])
            else:
                card_block = self._format_cards(cards, positions=positions)
            vars_ = self._prompt_vars(profile, question=question, cards=card_block)
            system = product_system("tarot_spread", level=level, variables=vars_)
            messages = [
                {"role": "system", "content": [{"type": "text", "text": system}]},
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_trigger("расклад Таро")}],
                },
            ]
            try:
                text = await self._complete_leia(
                    messages,
                    user_id=user_id,
                    feature=f"tarot_{level}",
                    question=question,
                )
            except Exception as exc:
                logger.warning("Tarot AI failed, using fallback: %s", exc)
                text = ""
            if not (text or "").strip():
                logger.warning("Tarot AI empty — fallback interpretation for user=%s", user_id)
                text = self._tarot_fallback_text(question, cards, level=level)
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

            vars_ = self._prompt_vars(profile)
            system = product_system("forecast", level="mini", variables=vars_)
            messages = [
                {"role": "system", "content": [{"type": "text", "text": system}]},
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_trigger("мини-матрицу судьбы")}],
                },
            ]
            return await self._complete_leia(
                messages, user_id=user_id, feature="portrait_mini", question="portrait_mini"
            )

    async def generate_portrait(self, user_id: str) -> str:
        return await self.generate_mini_portrait(user_id)

    async def generate_portrait_full(self, user_id: str) -> str:
        async with AsyncSessionLocal() as session:
            profile = await self._profile(session, user_id)
            if profile is None or profile.birth_date is None:
                return "Для портрета нужна дата рождения. Нажми /start и заполни анкету."

            vars_ = self._prompt_vars(profile)
            system = product_system("forecast", level="full", variables=vars_)
            messages = [
                {"role": "system", "content": [{"type": "text", "text": system}]},
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_trigger("полную матрицу судьбы")}],
                },
            ]
            return await self._complete_leia(
                messages, user_id=user_id, feature="portrait_full", question="portrait_full"
            )

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

            cards_text = ""
            chat_text = ""
            chat_images: list[str] = []
            if product_id == "question":
                cards = TarotService().draw_cards(1)
                cards_text = self._format_cards(cards, positions=["ключ"])
            elif product_id == "tarot_spread":
                cards = TarotService().draw_cards(4)
                cards_text = self._format_cards([cards[1]], positions=["что мешает"])
            elif product_id == "chat":
                chat_text, chat_images = self._parse_chat_extra(extra_context)

            vars_ = self._prompt_vars(
                profile,
                partner_bd=extra_context if product_id == "love" else "",
                question=extra_context if product_id in ("question", "tarot_spread") else "",
                cards=cards_text,
                chat_text=chat_text,
            )
            system = product_system(product_id, level="mini", variables=vars_)
            trigger = user_trigger(f"мини «{product.title}»")
            user_content = (
                self._chat_user_content(trigger, chat_images)
                if product_id == "chat" and chat_images
                else [{"type": "text", "text": trigger}]
            )
            messages = [
                {"role": "system", "content": [{"type": "text", "text": system}]},
                {"role": "user", "content": user_content},
            ]
            text = await self._complete_leia(
                messages,
                user_id=user_id,
                feature=f"product_{product_id}_mini",
                question=extra_context[:500] or product_id,
            )
            if (text or "").strip():
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
            text = await self._generate_full_in_session(
                session,
                user_id,
                product_id,
                extra_context=extra_context,
                payment_id=payment_id,
                use_entitlement=use_entitlement,
            )
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
        if product_id in ("love", "question", "tarot_spread", "chat") and not prefs:
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

        product = PRODUCTS.get(product_id)
        cards_text = ""
        chat_text = ""
        chat_images: list[str] = []
        if product_id == "question":
            cards = TarotService().draw_cards(3)
            cards_text = self._format_cards(cards)
        elif product_id == "chat":
            chat_text, chat_images = self._parse_chat_extra(extra_context)

        vars_ = self._prompt_vars(
            profile,
            partner_bd=extra_context if product_id == "love" else "",
            question=extra_context if product_id in ("question", "tarot_spread") else "",
            cards=cards_text,
            chat_text=chat_text,
        )
        system = product_system(product_id, level="full", variables=vars_)
        title = product.title if product else product_id
        trigger = user_trigger(f"полный «{title}»")
        user_content = (
            self._chat_user_content(trigger, chat_images)
            if product_id == "chat" and chat_images
            else [{"type": "text", "text": trigger}]
        )
        messages = [
            {"role": "system", "content": [{"type": "text", "text": system}]},
            {"role": "user", "content": user_content},
        ]
        try:
            text = await self._complete_leia(
                messages,
                user_id=user_id,
                feature=f"product_{product_id}_full",
                question=extra_context[:500] or product_id,
            )
        except Exception as exc:
            logger.warning("Full AI failed in-session for %s: %s", product_id, exc)
            text = ""
        if (text or "").strip():
            await self.record_usage(
                session, user_id, product_id, "full", payment_id=payment_id, content=text
            )
            if use_entitlement:
                await EntitlementService().consume_credit(session, user_id, product_id)
        return text
