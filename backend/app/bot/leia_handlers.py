"""Handlers for bot «Лея» — products, onboarding, menu."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.helpers import safe_callback_answer
from app.bot.leia_keyboards import (
    inline_after_full_reading,
    inline_after_mini,
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
from app.bot.leia_texts import (
    BTN_MENU,
    BTN_PROFILE,
    COMBO_OFFER,
    ENTITLED_FULL,
    LEIA_REPLY_BUTTONS,
    PACKAGE_PAYMENT,
    PAYMENT_LINK,
    PORTRAIT_LOADING,
    PRODUCT_LOADING,
    READING_FOLLOWUP_PROMPT,
)
from app.bot.rich_messages import answer_rich_message, present_rich_panel
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
from app.services.products.service import ProductService
from app.services.profile.service import ProfileService
from app.services.referrals.service import ReferralService

logger = logging.getLogger(__name__)
router = Router()


async def _db_user(telegram_id: int) -> User | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def _ensure_reply_keyboard(message: Message) -> None:
    await message.answer("‎", reply_markup=leia_reply_keyboard())


async def _typing(message: Message) -> None:
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)


async def show_leia_profile(message: Message) -> None:
    text = await build_leia_profile_text(
        message.from_user.id if message.from_user else message.chat.id
    )
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
    await present_rich_panel(message, text, reply_markup=inline_product_menu())


async def show_packages_menu(message: Message) -> None:
    await present_rich_panel(
        message,
        format_packages_menu_rich(),
        reply_markup=inline_packages_menu(),
    )


async def _deliver_full_reading(message: Message, text: str) -> None:
    await answer_rich_message(message, text, reply_markup=inline_after_full_reading())


async def complete_onboarding_flow(message: Message, telegram_id: int) -> None:
    user = await _db_user(telegram_id)
    if user is None:
        return

    await _typing(message)
    await message.answer(PORTRAIT_LOADING, reply_markup=leia_reply_keyboard())
    try:
        portrait = await ProductService().generate_portrait(user.id)
        await answer_rich_message(message, portrait, reply_markup=inline_product_menu())
    except Exception:
        logger.exception("Portrait generation failed for %s", telegram_id)
        await message.answer(
            "Портрет временно недоступен — но меню уже готово ✨",
            reply_markup=inline_product_menu(),
        )
    await present_rich_panel(
        message,
        normalize_leia_rich(COMBO_OFFER),
        reply_markup=inline_packages_menu(),
    )


@router.message(F.text.in_(LEIA_REPLY_BUTTONS))
async def leia_reply_buttons(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.text == BTN_MENU:
        await show_leia_menu(message)
        return
    if message.text == BTN_PROFILE:
        await show_leia_profile(message)


@router.callback_query(F.data == "leia:profile")
async def leia_profile_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    await show_leia_profile(callback.message)


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
        if flow.product_text:
            await _deliver_full_reading(message, flow.product_text)
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
    await _typing(message)
    await message.answer(ENTITLED_FULL)
    try:
        text = await ProductService().generate_full(
            user.id, product_id, extra_context=extra_context, use_entitlement=True
        )
        await _deliver_full_reading(message, text)
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
    await show_leia_menu(callback.message)


@router.callback_query(F.data == "leia:packages")
async def leia_packages(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    await show_packages_menu(callback.message)


@router.callback_query(F.data == "leia:referral")
async def leia_referral(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    bot_user = await callback.bot.get_me()
    link = ReferralService().build_referral_link(bot_user.username, callback.from_user.id)
    await present_rich_panel(
        callback.message,
        format_referral_friend_rich(link),
        reply_markup=inline_referral_share(link),
    )


@router.callback_query(F.data == "leia:followup")
async def leia_followup_start(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.set_state(BotStates.waiting_reading_followup)
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
    await present_rich_panel(
        callback.message,
        format_package_pitch_rich(package_id, active=active),
        reply_markup=inline_package_actions(package_id, active=active),
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
    await present_rich_panel(
        callback.message,
        format_product_pitch_rich(
            product_id, access_label=access_label, has_plan=has_plan
        ),
        reply_markup=inline_product_actions(product_id, access_label=access_label),
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
        await callback.answer("Сначала оформи пакет или оплати разбор", show_alert=True)
        return

    if product_id == "love":
        await state.set_state(BotStates.waiting_partner_birth_date)
        await state.update_data(product_id=product_id, mode="full_entitled")
        await callback.message.answer(PRODUCTS["love"].mini_hint)
        return
    if product_id == "question":
        await state.set_state(BotStates.waiting_product_question)
        await state.update_data(product_id=product_id, mode="full_entitled")
        await callback.message.answer(PRODUCTS["question"].mini_hint)
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
    if product_id == "question":
        await state.set_state(BotStates.waiting_product_question)
        await state.update_data(product_id=product_id, mode="mini")
        await callback.message.answer(product.mini_hint)
        return

    await _typing(callback.message)
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
    if product_id == "question":
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
    if not reading:
        await message.answer(
            "Сначала получи разбор — потом смогу ответить на вопросы к нему 💫",
            reply_markup=inline_product_menu(),
        )
        await state.clear()
        return

    user = await _db_user(message.from_user.id)
    name = "дорогая"
    if user:
        async with AsyncSessionLocal() as session:
            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            if profile and profile.name:
                name = profile.name

    await _typing(message)
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
    text = await ProductService().generate_mini(user.id, product_id, extra_context=question)
    access_label = await _product_access_label(user.id, product_id)
    await answer_rich_message(
        message, text, reply_markup=inline_after_mini(product_id, access_label=access_label)
    )
