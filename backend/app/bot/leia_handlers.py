"""Handlers for bot «Лея» — products, onboarding, menu."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.helpers import safe_callback_answer
from app.bot.leia_keyboards import (
    inline_after_mini,
    inline_legal_consent,
    inline_package_actions,
    inline_packages_menu,
    inline_product_actions,
    inline_product_menu,
    inline_skip_birth_time,
)
from app.bot.leia_texts import (
    COMBO_OFFER,
    ENTITLED_FULL,
    MENU_TEXT,
    PACKAGE_PAYMENT,
    PAYMENT_LINK,
    PORTRAIT_LOADING,
    PRODUCT_LOADING,
    WELCOME_BACK,
)
from app.bot.rich_messages import answer_rich_message, present_rich_panel
from app.bot.states import BotStates
from app.database.models import SoulProfile, User
from app.database.session import AsyncSessionLocal
from app.services.billing.providers import PaymentFlowResult
from app.services.onboarding.service import OnboardingService
from app.services.products.catalog import PRODUCTS
from app.services.products.entitlements import EntitlementService
from app.services.products.packages import PACKAGES
from app.services.products.service import ProductService
from app.services.profile.service import ProfileService

logger = logging.getLogger(__name__)
router = Router()


async def _db_user(telegram_id: int) -> User | None:
    async with AsyncSessionLocal() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def show_leia_menu(message: Message, *, edit: Message | None = None) -> None:
    telegram_id = message.from_user.id if message.from_user else message.chat.id
    user = await _db_user(telegram_id)
    plan = None
    if user:
        plan = await EntitlementService().active_plan_label(user.id)
    text = f"{WELCOME_BACK}\n\n{MENU_TEXT}"
    if plan:
        text = f"{WELCOME_BACK}\n{plan}\n\n{MENU_TEXT}"
    await present_rich_panel(
        message,
        text,
        reply_markup=inline_product_menu(),
        edit_message=edit,
    )


async def complete_onboarding_flow(message: Message, telegram_id: int) -> None:
    user = await _db_user(telegram_id)
    if user is None:
        return

    await message.answer(PORTRAIT_LOADING)
    try:
        portrait = await ProductService().generate_portrait(user.id)
        await answer_rich_message(message, portrait, reply_markup=inline_product_menu())
    except Exception:
        logger.exception("Portrait generation failed for %s", telegram_id)
        await message.answer(
            "Портрет временно недоступен — но меню уже готово ✨",
            reply_markup=inline_product_menu(),
        )
    await message.answer(COMBO_OFFER, reply_markup=inline_packages_menu())


def onboarding_markup_for_step(step_key: str):
    if step_key == "legal_consent":
        return inline_legal_consent()
    if step_key == "birth_time":
        return inline_skip_birth_time()
    return None


async def _product_entitled(user_id: str, product_id: str) -> bool:
    return await EntitlementService().can_use_full_free(user_id, product_id)


async def _deliver_payment_flow(message: Message, flow: PaymentFlowResult) -> None:
    if flow.completed:
        if flow.product_text:
            await answer_rich_message(
                message, flow.product_text, reply_markup=inline_product_menu()
            )
        elif flow.user_text:
            await message.answer(flow.user_text, reply_markup=inline_product_menu())
        else:
            await message.answer(
                f"✅ Оплата прошла — {flow.amount_rub} ₽",
                reply_markup=inline_product_menu(),
            )
        return
    if flow.payment_url:
        await message.answer(PAYMENT_LINK.format(url=flow.payment_url))


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
    await show_leia_menu(callback.message, edit=callback.message)


@router.callback_query(F.data == "leia:packages")
async def leia_packages(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    await present_rich_panel(
        callback.message,
        "📦 **Пакеты и подписки**\n\nВыбери вариант — каждый выгоднее разовых покупок.",
        reply_markup=inline_packages_menu(),
        edit_message=callback.message,
    )


@router.callback_query(F.data.startswith("leia:package:"))
async def leia_package_pitch(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    package_id = callback.data.removeprefix("leia:package:")
    package = PACKAGES.get(package_id)
    if package is None:
        return
    await present_rich_panel(
        callback.message,
        package.pitch,
        reply_markup=inline_package_actions(package_id),
        edit_message=callback.message,
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
    entitled = bool(user and await _product_entitled(user.id, product_id))
    await present_rich_panel(
        callback.message,
        product.pitch,
        reply_markup=inline_product_actions(product_id, entitled=entitled),
        edit_message=callback.message,
    )


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

    await callback.message.answer(PRODUCT_LOADING)
    try:
        text = await ProductService().generate_mini(user.id, product_id)
        entitled = await _product_entitled(user.id, product_id)
        await answer_rich_message(
            callback.message, text, reply_markup=inline_after_mini(product_id, entitled=entitled)
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
        await callback.message.answer(ENTITLED_FULL)
        try:
            text = await service.generate_full(user.id, product_id, use_entitlement=True)
            await answer_rich_message(callback.message, text, reply_markup=inline_product_menu())
        except Exception:
            logger.exception("Entitled full failed")
            await callback.message.answer("Не получилось сейчас — попробуй чуть позже.")
        return

    try:
        flow = await service.create_full_payment(user, product_id)
        await _deliver_payment_flow(callback.message, flow)
    except Exception as exc:
        logger.exception("Payment create failed")
        await callback.message.answer(f"Оплата временно недоступна. ({exc})")


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

    await state.clear()
    user = await _db_user(message.from_user.id)
    if user is None:
        return

    if mode == "full_pay":
        try:
            flow = await ProductService().create_full_payment(
                user, product_id, extra_context=partner_info
            )
            await _deliver_payment_flow(message, flow)
        except Exception:
            await message.answer("Оплата временно недоступна.")
        return

    if mode == "full_entitled":
        await message.answer(ENTITLED_FULL)
        try:
            text = await ProductService().generate_full(
                user.id, product_id, extra_context=partner_info, use_entitlement=True
            )
            await answer_rich_message(message, text, reply_markup=inline_product_menu())
        except Exception:
            await message.answer("Не получилось сейчас — попробуй чуть позже.")
        return

    await message.answer(PRODUCT_LOADING)
    text = await ProductService().generate_mini(user.id, product_id, extra_context=partner_info)
    entitled = await _product_entitled(user.id, product_id)
    await answer_rich_message(
        message, text, reply_markup=inline_after_mini(product_id, entitled=entitled)
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
    await state.clear()
    user = await _db_user(message.from_user.id)
    if user is None:
        return

    if mode == "full_pay":
        try:
            flow = await ProductService().create_full_payment(
                user, product_id, extra_context=question
            )
            await _deliver_payment_flow(message, flow)
        except Exception:
            await message.answer("Оплата временно недоступна.")
        return

    if mode == "full_entitled":
        await message.answer(ENTITLED_FULL)
        try:
            text = await ProductService().generate_full(
                user.id, product_id, extra_context=question, use_entitlement=True
            )
            await answer_rich_message(message, text, reply_markup=inline_product_menu())
        except Exception:
            await message.answer("Не получилось сейчас — попробуй чуть позже.")
        return

    await message.answer(PRODUCT_LOADING)
    text = await ProductService().generate_mini(user.id, product_id, extra_context=question)
    entitled = await _product_entitled(user.id, product_id)
    await answer_rich_message(
        message, text, reply_markup=inline_after_mini(product_id, entitled=entitled)
    )
