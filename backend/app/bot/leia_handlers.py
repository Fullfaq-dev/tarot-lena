"""Handlers for bot «Лея» — products, onboarding, menu."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.helpers import safe_callback_answer
from app.bot.leia_assets import send_leia_photo
from app.bot.leia_panel import callback_leia_scene, present_leia_scene
from app.bot.leia_keyboards import (
    inline_after_full_reading,
    inline_after_mini,
    inline_evening_reading,
    inline_funnel_day2_topics,
    inline_legal_consent,
    inline_package_actions,
    inline_packages_menu,
    inline_product_actions,
    inline_product_menu,
    inline_referral_share,
    inline_skip_birth_time,
    leia_reply_keyboard,
)
from app.bot.leia_rich import (
    format_leia_menu_rich,
    format_package_pitch_rich,
    format_packages_menu_rich,
    format_product_pitch_rich,
    format_referral_friend_rich,
    normalize_leia_rich,
)
from app.bot.cards_media import send_card_with_caption, send_tarot_reading_rich
from app.bot.leia_texts import (
    BTN_MENU,
    BTN_PROFILE,
    COMBO_OFFER,
    ENTITLED_FULL,
    LEIA_REPLY_BUTTONS,
    PACKAGE_PAYMENT,
    PAYMENT_LINK,
    PAID_CHAT_LOADING,
    PORTRAIT_LOADING,
    PRODUCT_LOADING,
    POST_READING_CHAT_HINT,
    READING_FOLLOWUP_PROMPT,
)
from app.bot.rich_messages import answer_rich_message
from app.bot.states import BotStates
from app.database.models import SoulProfile, User
from app.database.session import AsyncSessionLocal
from app.services.billing.providers import PaymentFlowResult
from app.services.onboarding.service import OnboardingService
from app.services.products.catalog import PRODUCTS
from app.services.products.entitlements import EntitlementService
from app.services.products.followup import ReadingFollowupService
from app.services.products.packages import PACKAGES
from app.services.products.profile_view import build_leia_profile_text
from app.services.products.chat import LeiaChatService
from app.services.products.service import ProductService
from app.services.profile.service import ProfileService
from app.services.referrals.service import ReferralService
from app.services.tarot.service import TarotService

logger = logging.getLogger(__name__)
router = Router()


async def _db_user(telegram_id: int) -> User | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def _ensure_reply_keyboard(message: Message) -> None:
    """Attach bottom reply keyboard; Telegram rejects empty/invisible-only text."""
    from aiogram.exceptions import TelegramBadRequest

    markup = leia_reply_keyboard()
    for text in ("\u2800", "👇"):
        try:
            await message.answer(text, reply_markup=markup)
            return
        except TelegramBadRequest:
            continue


async def show_leia_profile(message: Message, *, telegram_id: int | None = None) -> None:
    tid = telegram_id
    if tid is None:
        tid = message.from_user.id if message.from_user else message.chat.id
    text = await build_leia_profile_text(tid)
    await answer_rich_message(
        message,
        text,
        reply_markup=inline_product_menu(),
    )


async def show_leia_menu(message: Message) -> None:
    telegram_id = message.from_user.id if message.from_user else message.chat.id
    user = await _db_user(telegram_id)
    plan = None
    if user:
        plan = await EntitlementService().active_plan_label(user.id)
    text = format_leia_menu_rich(plan_label=plan)
    await present_leia_scene(message, text, reply_markup=inline_product_menu())


async def show_packages_menu(message: Message) -> None:
    await present_leia_scene(
        message,
        format_packages_menu_rich(),
        reply_markup=inline_packages_menu(),
        image_key="packages",
    )


async def _store_reading_state(state: FSMContext | None, text: str, product_id: str) -> None:
    excerpt = (text or "").strip()[:4000]
    if not excerpt or state is None:
        return
    await state.update_data(
        last_reading_text=excerpt,
        last_product_id=product_id,
    )


async def _deliver_tarot_spread(
    message: Message,
    *,
    question: str,
    text: str,
    cards: list[dict],
    product_id: str,
    level: str,
    state: FSMContext | None = None,
) -> None:
    if not cards:
        if level == "full":
            await _deliver_full_reading(message, text, state=state, product_id=product_id)
        else:
            access_label = None
            user = await _db_user(message.from_user.id if message.from_user else message.chat.id)
            if user:
                access_label = await _product_access_label(user.id, product_id)
            await answer_rich_message(
                message, text, reply_markup=inline_after_mini(product_id, access_label=access_label)
            )
        await _store_reading_state(state, text, product_id)
        return

    label = "Расклад Таро"
    markup = inline_after_full_reading() if level == "full" else None
    if level == "mini":
        user = await _db_user(message.from_user.id if message.from_user else message.chat.id)
        access_label = None
        if user:
            access_label = await _product_access_label(user.id, product_id)
        markup = inline_after_mini(product_id, access_label=access_label)

    await send_tarot_reading_rich(
        message,
        label=label,
        question=question,
        reading_type="spread",
        cards=cards,
        interpretation=text,
        lang="ru",
        reply_markup=markup,
    )
    if level == "full" and not (text or "").strip():
        await message.answer(
            "⚠️ Расшифровка не сгенерировалась — нажми «Задать вопрос к разбору» "
            "или напиши в чат, и я отвечу по картам."
        )
    elif level == "full":
        await message.answer(POST_READING_CHAT_HINT)
    await _store_reading_state(state, text, product_id)


async def _deliver_full_reading(message: Message, text: str, *, state: FSMContext | None = None, product_id: str = "") -> None:
    await answer_rich_message(message, text, reply_markup=inline_after_full_reading())
    await message.answer(POST_READING_CHAT_HINT)
    if product_id:
        await _store_reading_state(state, text, product_id)


async def complete_onboarding_flow(message: Message, telegram_id: int) -> None:
    user = await _db_user(telegram_id)
    if user is None:
        return

    await message.answer(PORTRAIT_LOADING, reply_markup=leia_reply_keyboard())
    try:
        portrait = await ProductService().generate_mini_portrait(user.id)
        await send_leia_photo(message, "portrait")
        await answer_rich_message(message, portrait, reply_markup=inline_product_menu())
        async with AsyncSessionLocal() as session:
            from datetime import UTC, datetime

            from app.database.models import UserSettings

            settings = await session.scalar(
                select(UserSettings).where(UserSettings.user_id == user.id)
            )
            if settings:
                settings.mini_portrait_sent_at = datetime.now(UTC)
                await session.commit()
    except Exception:
        logger.exception("Portrait generation failed for %s", telegram_id)
        await message.answer(
            "Портрет временно недоступен — но меню уже готово ✨",
            reply_markup=inline_product_menu(),
        )
    await present_leia_scene(
        message,
        normalize_leia_rich(COMBO_OFFER),
        reply_markup=inline_packages_menu(),
        image_key="packages",
    )


@router.message(F.text.in_(LEIA_REPLY_BUTTONS))
async def leia_reply_buttons(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.text == BTN_MENU:
        await show_leia_menu(message)
        return
    if message.text == BTN_PROFILE:
        await show_leia_profile(message)
        await _ensure_reply_keyboard(message)
        return


@router.callback_query(F.data == "leia:profile")
async def leia_profile_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    await show_leia_profile(callback.message, telegram_id=callback.from_user.id)


def onboarding_markup_for_step(step_key: str):
    if step_key == "legal_consent":
        return inline_legal_consent()
    if step_key == "birth_time":
        return inline_skip_birth_time()
    return None


async def _product_entitled(user_id: str, product_id: str) -> bool:
    return await EntitlementService().can_use_full_free(user_id, product_id)


async def _product_access_label(user_id: str, product_id: str) -> str | None:
    return await EntitlementService().full_access_label(user_id, product_id)


async def _deliver_payment_flow(
    message: Message, flow: PaymentFlowResult, *, state: FSMContext | None = None
) -> None:
    if flow.completed:
        if flow.product_text and flow.product_id == "tarot_spread" and flow.tarot_cards:
            await _deliver_tarot_spread(
                message,
                question=flow.tarot_question or "",
                text=flow.product_text,
                cards=list(flow.tarot_cards),
                product_id="tarot_spread",
                level="full",
                state=state,
            )
        elif flow.product_text:
            pid = flow.product_id or "question"
            await _deliver_full_reading(
                message, flow.product_text, state=state, product_id=pid
            )
            if state is not None:
                await state.update_data(last_reading_text=flow.product_text[:4000])
        elif flow.user_text:
            await message.answer(flow.user_text)
            await show_leia_menu(message)
        else:
            await message.answer(f"✅ Оплата прошла — {flow.amount_rub} ₽")
            await show_leia_menu(message)
        return
    if flow.payment_url:
        await message.answer(PAYMENT_LINK.format(url=flow.payment_url))


async def _run_entitled_full(
    message: Message,
    *,
    user: User,
    product_id: str,
    extra_context: str = "",
    state: FSMContext | None = None,
) -> None:
    await message.answer(ENTITLED_FULL)
    try:
        service = ProductService()
        if product_id == "tarot_spread":
            question = extra_context or "Мой вопрос"
            text, cards = await service.generate_tarot_spread(
                user.id,
                question,
                level="full",
                use_entitlement=True,
            )
            await _deliver_tarot_spread(
                message,
                question=question,
                text=text,
                cards=cards,
                product_id=product_id,
                level="full",
                state=state,
            )
            return
        text = await service.generate_full(
            user.id, product_id, extra_context=extra_context, use_entitlement=True
        )
        await _deliver_full_reading(message, text, state=state, product_id=product_id)
        if state is not None:
            await state.update_data(
                last_reading_text=text[:4000],
                last_product_id=product_id,
            )
    except Exception:
        logger.exception("Entitled full failed")
        await message.answer("Не получилось сейчас — попробуй чуть позже.")


@router.callback_query(F.data == "leia:consent")
async def leia_consent(callback: CallbackQuery) -> None:
    await safe_callback_answer(callback)
    service = OnboardingService()
    prompt, _ = await service.advance_from_consent(callback.from_user)
    if prompt:
        await callback.message.answer(prompt)


@router.callback_query(F.data == "leia:skip_time")
async def leia_skip_time(callback: CallbackQuery) -> None:
    await safe_callback_answer(callback)
    service = OnboardingService()
    reply, _, completed = await service.skip_birth_time(callback.from_user)
    if not reply:
        return
    if completed:
        await callback.message.answer(reply)
        await complete_onboarding_flow(callback.message, callback.from_user.id)
    else:
        markup = onboarding_markup_for_step("birth_city")
        await callback.message.answer(reply, reply_markup=markup)


@router.callback_query(F.data == "leia:menu")
async def leia_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    if callback.message is None:
        return
    telegram_id = callback.from_user.id
    user = await _db_user(telegram_id)
    plan = None
    if user:
        plan = await EntitlementService().active_plan_label(user.id)
    await callback_leia_scene(
        callback,
        format_leia_menu_rich(plan_label=plan),
        reply_markup=inline_product_menu(),
    )


@router.callback_query(F.data == "leia:packages")
async def leia_packages(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    await callback_leia_scene(
        callback,
        format_packages_menu_rich(),
        reply_markup=inline_packages_menu(),
        image_key="packages",
    )


@router.callback_query(F.data == "leia:referral")
async def leia_referral(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    bot_user = await callback.bot.get_me()
    link = ReferralService().build_referral_link(bot_user.username, callback.from_user.id)
    await callback_leia_scene(
        callback,
        format_referral_friend_rich(link),
        reply_markup=inline_referral_share(link),
        image_key="referral",
    )


@router.callback_query(F.data == "leia:followup")
async def leia_followup_start(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    reading = ""
    user = await _db_user(callback.from_user.id)
    if user:
        reading = await ProductService().latest_reading_context(user.id)
    await state.set_state(BotStates.waiting_reading_followup)
    if reading:
        await state.update_data(last_reading_text=reading[:4000])
    await callback.message.answer(READING_FOLLOWUP_PROMPT)


@router.callback_query(F.data.startswith("leia:package:"))
async def leia_package_pitch(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    package_id = callback.data.removeprefix("leia:package:")
    package = PACKAGES.get(package_id)
    if package is None:
        return
    active = False
    user = await _db_user(callback.from_user.id)
    if user:
        ent = EntitlementService()
        if package_id == "vip":
            active = await ent.has_vip(user.id)
        elif package_id == "love_plus":
            active = await ent.has_love_plus(user.id)
    await callback_leia_scene(
        callback,
        format_package_pitch_rich(package_id, active=active),
        reply_markup=inline_package_actions(package_id, active=active),
        image_key="packages",
    )


@router.callback_query(F.data.startswith("leia:buy:"))
async def leia_buy_package(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    package_id = callback.data.removeprefix("leia:buy:")
    if package_id not in PACKAGES:
        return
    user = await _db_user(callback.from_user.id)
    if user is None:
        return
    try:
        flow = await ProductService().create_package_payment(user, package_id)
        if flow.completed:
            await _deliver_payment_flow(callback.message, flow)
        else:
            await callback.message.answer(PACKAGE_PAYMENT.format(url=flow.payment_url))
    except Exception as exc:
        logger.exception("Package payment create failed")
        await callback.message.answer(f"Оплата временно недоступна. ({exc})")


@router.callback_query(F.data.startswith("leia:product:"))
async def leia_product_pitch(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    product_id = callback.data.removeprefix("leia:product:")
    product = PRODUCTS.get(product_id)
    if product is None:
        return
    user = await _db_user(callback.from_user.id)
    ent = EntitlementService()
    access_label = None
    has_plan = False
    if user:
        access_label = await _product_access_label(user.id, product_id)
        has_plan = await ent.has_any_plan(user.id)
    await callback_leia_scene(
        callback,
        format_product_pitch_rich(
            product_id, access_label=access_label, has_plan=has_plan
        ),
        reply_markup=inline_product_actions(product_id, access_label=access_label),
        image_key=product_id,
    )


@router.callback_query(F.data.startswith("leia:launch:"))
async def leia_launch(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    product_id = callback.data.removeprefix("leia:launch:")
    if product_id not in PRODUCTS:
        return
    user = await _db_user(callback.from_user.id)
    if user is None:
        return
    if not await _product_entitled(user.id, product_id):
        await safe_callback_answer(callback)
        access_label = await _product_access_label(user.id, product_id)
        has_plan = await EntitlementService().has_any_plan(user.id)
        await callback_leia_scene(
            callback,
            format_product_pitch_rich(
                product_id, access_label=access_label, has_plan=has_plan
            ),
            reply_markup=inline_product_actions(product_id, access_label=access_label),
            image_key=product_id,
        )
        return

    if product_id == "love":
        await state.set_state(BotStates.waiting_partner_birth_date)
        await state.update_data(product_id=product_id, mode="full_entitled")
        await callback.message.answer(PRODUCTS["love"].mini_hint)
        return
    if product_id in ("question", "tarot_spread"):
        await state.set_state(BotStates.waiting_product_question)
        await state.update_data(product_id=product_id, mode="full_entitled")
        await callback.message.answer(PRODUCTS[product_id].mini_hint)
        return

    await _run_entitled_full(callback.message, user=user, product_id=product_id, state=state)


@router.callback_query(F.data.startswith("leia:mini:"))
async def leia_mini(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    product_id = callback.data.removeprefix("leia:mini:")
    product = PRODUCTS.get(product_id)
    if product is None:
        return

    user = await _db_user(callback.from_user.id)
    if user is None:
        return
    if await ProductService().has_mini(user.id, product_id):
        await callback.answer("Мини-версия уже была — попробуй полную 🔓", show_alert=True)
        return

    if product_id == "love":
        await state.set_state(BotStates.waiting_partner_birth_date)
        await state.update_data(product_id=product_id, mode="mini")
        await callback.message.answer(product.mini_hint)
        return
    if product_id in ("question", "tarot_spread"):
        await state.set_state(BotStates.waiting_product_question)
        await state.update_data(product_id=product_id, mode="mini")
        await callback.message.answer(product.mini_hint)
        return

    await callback.message.answer(PRODUCT_LOADING)
    try:
        text = await ProductService().generate_mini(user.id, product_id)
        access_label = await _product_access_label(user.id, product_id)
        await answer_rich_message(
            callback.message, text, reply_markup=inline_after_mini(product_id, access_label=access_label)
        )
    except Exception:
        logger.exception("Mini product failed")
        await callback.message.answer("Не получилось сейчас — попробуй чуть позже.")


@router.callback_query(F.data.startswith("leia:full:"))
async def leia_full_pay(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    product_id = callback.data.removeprefix("leia:full:")
    product = PRODUCTS.get(product_id)
    if product is None:
        return

    user = await _db_user(callback.from_user.id)
    if user is None:
        return
    service = ProductService()
    if await service.is_full_blocked(user.id, product_id):
        await callback.answer("Полная версия уже есть ✨", show_alert=True)
        return

    entitled = await _product_entitled(user.id, product_id)

    if product_id == "love":
        await state.set_state(BotStates.waiting_partner_birth_date)
        await state.update_data(
            product_id=product_id,
            mode="full_entitled" if entitled else "full_pay",
        )
        await callback.message.answer(product.mini_hint)
        return
    if product_id in ("question", "tarot_spread"):
        await state.set_state(BotStates.waiting_product_question)
        await state.update_data(
            product_id=product_id,
            mode="full_entitled" if entitled else "full_pay",
        )
        await callback.message.answer(product.mini_hint)
        return

    if entitled:
        await _run_entitled_full(callback.message, user=user, product_id=product_id, state=state)
        return

    try:
        flow = await service.create_full_payment(user, product_id)
        await _deliver_payment_flow(callback.message, flow)
    except Exception as exc:
        logger.exception("Payment create failed")
        await callback.message.answer(f"Оплата временно недоступна. ({exc})")


@router.message(BotStates.waiting_reading_followup)
async def reading_followup(message: Message, state: FSMContext) -> None:
    question = (message.text or "").strip()
    if len(question) < 2:
        await message.answer("Напиши вопрос чуть подробнее 🙏")
        return
    data = await state.get_data()
    reading = str(data.get("last_reading_text", "")).strip()
    user = await _db_user(message.from_user.id)
    if not reading and user:
        reading = await ProductService().latest_reading_context(user.id)
        if reading:
            await state.update_data(last_reading_text=reading[:4000])

    name = "дорогая"
    if user:
        async with AsyncSessionLocal() as session:
            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            if profile and profile.name:
                name = profile.name

    chat = LeiaChatService()
    if not reading and user and await chat.has_open_chat(user.id):
        await message.answer(PAID_CHAT_LOADING)
        try:
            reply = await chat.answer_freeform(user.id, name, question)
            await answer_rich_message(message, reply, reply_markup=inline_after_full_reading())
        except Exception:
            logger.exception("VIP followup chat failed")
            await message.answer(
                "Не получилось ответить сейчас — попробуй переформулировать вопрос.",
                reply_markup=inline_after_full_reading(),
            )
        return

    if not reading:
        await message.answer(
            "Не вижу текст последнего разбора — выбери продукт в меню или сделай новый расклад.",
            reply_markup=inline_after_full_reading(),
        )
        await state.clear()
        return

    await message.answer("Думаю над твоим вопросом…")
    try:
        answer = await ReadingFollowupService().answer(
            reading_excerpt=reading,
            question=question,
            user_name=name,
        )
        await answer_rich_message(message, answer, reply_markup=inline_after_full_reading())
    except Exception:
        logger.exception("Reading followup failed")
        await message.answer("Не получилось ответить сейчас — попробуй переформулировать вопрос.")


@router.message(BotStates.waiting_partner_birth_date)
async def partner_birth_date(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    product_id = data.get("product_id", "love")
    mode = data.get("mode", "mini")
    raw = (message.text or "").strip()
    parsed = ProfileService()._parse_birth_date(raw)
    if parsed is None:
        await message.answer("Формат: ДД.ММ.ГГГГ — например 15.06.1990")
        return

    partner_info = f"ДР партнёра: {parsed.strftime('%d.%m.%Y')}"
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if user:
            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            if profile:
                prefs = dict(profile.preferences or {})
                prefs["partner_birth_date"] = parsed.isoformat()
                profile.preferences = prefs
                await session.commit()

    user = await _db_user(message.from_user.id)
    if user is None:
        await state.clear()
        return

    if mode == "full_pay":
        await state.clear()
        try:
            flow = await ProductService().create_full_payment(
                user, product_id, extra_context=partner_info
            )
            await _deliver_payment_flow(message, flow)
        except Exception:
            await message.answer("Оплата временно недоступна.")
        return

    if mode == "full_entitled":
        await _run_entitled_full(
            message, user=user, product_id=product_id, extra_context=partner_info, state=state
        )
        await state.clear()
        return

    await state.clear()
    await message.answer(PRODUCT_LOADING)
    text = await ProductService().generate_mini(user.id, product_id, extra_context=partner_info)
    access_label = await _product_access_label(user.id, product_id)
    await answer_rich_message(
        message, text, reply_markup=inline_after_mini(product_id, access_label=access_label)
    )


@router.message(BotStates.waiting_product_question)
async def product_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    product_id = data.get("product_id", "question")
    mode = data.get("mode", "mini")
    question = (message.text or "").strip()
    if len(question) < 3:
        await message.answer("Напиши вопрос чуть подробнее 🙏")
        return

    user = await _db_user(message.from_user.id)
    if user is None:
        await state.clear()
        return

    if mode == "full_pay":
        await state.clear()
        try:
            flow = await ProductService().create_full_payment(
                user, product_id, extra_context=question
            )
            await _deliver_payment_flow(message, flow)
        except Exception:
            await message.answer("Оплата временно недоступна.")
        return

    if mode == "full_entitled":
        await _run_entitled_full(
            message, user=user, product_id=product_id, extra_context=question, state=state
        )
        await state.clear()
        return

    await state.clear()
    await message.answer(PRODUCT_LOADING)
    service = ProductService()
    if product_id == "tarot_spread":
        text, cards = await service.generate_tarot_spread(user.id, question, level="mini")
        await _deliver_tarot_spread(
            message,
            question=question,
            text=text,
            cards=cards,
            product_id=product_id,
            level="mini",
        )
        return
    text = await service.generate_mini(user.id, product_id, extra_context=question)
    access_label = await _product_access_label(user.id, product_id)
    await answer_rich_message(
        message, text, reply_markup=inline_after_mini(product_id, access_label=access_label)
    )


_FUNNEL_TOPICS = {
    "love": "love",
    "wealth": "wealth",
    "advice": "forecast",
}


@router.callback_query(F.data == "leia:evening_reading")
async def leia_evening_reading(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    if callback.message is None:
        return
    cards = TarotService().draw_cards(1)
    card = cards[0] if cards else {"name": "Звезда", "description": "надежда и покой"}
    from app.services.broadcasts.content import format_evening_reading

    insight = str(card.get("description", "Отпусти лишнее — завтра новый день."))[:280]
    text = format_evening_reading(
        card_name=str(card.get("name", "Карта")),
        card_meaning=str(card.get("description", "важный урок дня")),
        insight=insight,
    )
    sent = await send_card_with_caption(
        callback.message,
        card,
        caption_html=str(card.get("name", "Карта")),
        caption_plain=str(card.get("name", "Карта")),
    )
    if not sent:
        await callback.message.answer(f"🃏 {card.get('name', 'Карта')}")
    await answer_rich_message(callback.message, text, reply_markup=inline_product_menu())


@router.callback_query(F.data.startswith("leia:funnel:"))
async def leia_funnel_topic(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    if callback.message is None:
        return
    topic = callback.data.removeprefix("leia:funnel:")
    product_id = _FUNNEL_TOPICS.get(topic)
    if product_id is None:
        return
    user = await _db_user(callback.from_user.id)
    if user is None:
        return
    service = ProductService()
    if await service.has_mini(user.id, product_id):
        access_label = await _product_access_label(user.id, product_id)
        has_plan = await EntitlementService().has_any_plan(user.id)
        await callback_leia_scene(
            callback,
            format_product_pitch_rich(
                product_id, access_label=access_label, has_plan=has_plan
            ),
            reply_markup=inline_product_actions(product_id, access_label=access_label),
            image_key=product_id,
        )
        return
    await callback.message.answer(PRODUCT_LOADING)
    try:
        text = await service.generate_mini(user.id, product_id)
        access_label = await _product_access_label(user.id, product_id)
        await send_leia_photo(callback.message, product_id)
        await answer_rich_message(
            callback.message,
            text,
            reply_markup=inline_after_mini(product_id, access_label=access_label),
        )
    except Exception:
        logger.exception("Funnel mini failed for %s", product_id)
        await callback.message.answer("Не получилось сейчас — попробуй из меню чуть позже.")
