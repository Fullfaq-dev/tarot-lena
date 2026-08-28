"""Handlers for bot «Лея» — products, onboarding, menu."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.bot.helpers import (
    refuse_if_busy_callback,
    refuse_if_busy_message,
    run_busy_job,
    safe_callback_answer,
)
from app.bot.leia_panel import answer_leia_rich, callback_leia_scene, present_leia_scene
from app.bot.leia_keyboards import (
    inline_after_full_reading,
    inline_after_mini,
    inline_chat_collect,
    inline_chat_role,
    inline_evening_reading,
    inline_funnel_day2_topics,
    inline_gender_choice,
    inline_history_item,
    inline_history_menu,
    inline_legal_consent,
    inline_leia_edit_menu,
    inline_package_actions,
    inline_packages_menu,
    inline_payment_button,
    inline_product_actions,
    inline_product_menu,
    inline_profile_actions,
    inline_referral_share,
    inline_skip_birth_time,
    leia_reply_keyboard,
)
from app.bot.leia_rich import (
    format_history_list_rich,
    format_leia_menu_rich,
    format_package_pitch_rich,
    format_packages_menu_rich,
    format_product_pitch_rich,
    format_referral_friend_rich,
)
from app.bot.cards_media import send_card_with_caption, send_tarot_reading_rich
from app.bot.leia_texts import (
    BTN_HISTORY,
    BTN_MENU,
    BTN_PROFILE,
    ENTITLED_FULL,
    LEIA_REPLY_BUTTONS,
    ONBOARDING_PROMPTS,
    PACKAGE_PAYMENT,
    PAYMENT_LINK,
    PAID_CHAT_LOADING,
    PORTRAIT_LOADING,
    PRODUCT_LOADING,
    READING_FOLLOWUP_PROMPT,
)
from app.bot.rich_messages import answer_rich_message
from app.bot.states import BotStates
from app.database.models import SoulProfile, User
from app.database.session import AsyncSessionLocal
from app.services.billing.providers import PaymentFlowResult
from app.services.onboarding.service import PROFILE_EDIT_FIELDS, OnboardingService
from app.services.products.catalog import PRODUCTS
from app.services.products.entitlements import EntitlementService
from app.services.products.followup import ReadingFollowupService
from app.services.products.packages import PACKAGES
from app.services.products.profile_view import build_leia_profile_text
from app.services.products.chat import LeiaChatService
from app.services.products.service import ProductService
from app.services.profile.service import ProfileService

_GENDER_VALUES = {
    "female": "женский",
    "male": "мужской",
    "skip": "не указывать",
}
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
        reply_markup=inline_profile_actions(),
    )


async def show_leia_history(
    message: Message,
    *,
    page: int = 0,
    telegram_id: int | None = None,
) -> None:
    # callback.message.from_user is the bot — callers must pass telegram_id.
    tid = telegram_id
    if tid is None and message.from_user is not None:
        tid = message.from_user.id
    if tid is None:
        tid = message.chat.id
    user = await _db_user(tid)
    if user is None:
        await message.answer("Сначала нажми /start")
        return
    items, page, total_pages = await ProductService().history_page(user.id, page)
    text = format_history_list_rich(page=page, total_pages=total_pages, count=len(items))
    await answer_rich_message(
        message,
        text,
        reply_markup=inline_history_menu(items, page, total_pages),
    )


async def _ensure_onboarded_or_restart(message: Message, telegram_id: int) -> User | None:
    """If user missing / not onboarded — send onboarding, not the product menu."""
    user = await _db_user(telegram_id)
    if user and user.is_onboarded:
        return user
    service = OnboardingService()
    tg_user = message.from_user
    if tg_user is None:
        await message.answer("Нажми /start")
        return None
    text, _, _ = await service.start_or_resume(tg_user)
    step_key = await service.get_current_step_key(tg_user) or "legal_consent"
    await answer_rich_message(
        message,
        text,
        reply_markup=onboarding_markup_for_step(step_key),
    )
    return None


async def show_leia_menu(message: Message) -> None:
    telegram_id = message.from_user.id if message.from_user else message.chat.id
    user = await _ensure_onboarded_or_restart(message, telegram_id)
    if user is None:
        return
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
    await _store_reading_state(state, text, product_id)


async def _deliver_full_reading(message: Message, text: str, *, state: FSMContext | None = None, product_id: str = "") -> None:
    await answer_rich_message(message, text, reply_markup=inline_after_full_reading())
    if product_id:
        await _store_reading_state(state, text, product_id)


async def complete_onboarding_flow(message: Message, telegram_id: int) -> None:
    user = await _db_user(telegram_id)
    if user is None:
        return

    try:
        await message.answer("✨ Анкета готова!", reply_markup=leia_reply_keyboard())
        portrait = await run_busy_job(
            message,
            lambda: ProductService().generate_mini_portrait(user.id),
            loading_text=PORTRAIT_LOADING,
            progress_text="🔮 Ещё считаю матрицу… почти готово",
            telegram_id=telegram_id,
            label="portrait",
        )
        if portrait is None:
            return
        await answer_leia_rich(
            message,
            portrait,
            reply_markup=inline_product_menu(),
            image_key="portrait",
        )
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
    await _ensure_reply_keyboard(message)


@router.message(F.text.in_(LEIA_REPLY_BUTTONS))
async def leia_reply_buttons(message: Message, state: FSMContext) -> None:
    await state.clear()
    tid = message.from_user.id if message.from_user else message.chat.id
    user = await _db_user(tid)
    if user is None or not user.is_onboarded:
        await _ensure_onboarded_or_restart(message, tid)
        return
    if message.text == BTN_MENU:
        await show_leia_menu(message)
        return
    if message.text == BTN_HISTORY:
        await show_leia_history(message, telegram_id=tid)
        return
    if message.text == BTN_PROFILE:
        await show_leia_profile(message, telegram_id=tid)
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
    if step_key == "gender":
        return inline_gender_choice()
    if step_key == "birth_time":
        return inline_skip_birth_time()
    return None


@router.callback_query(F.data.startswith("leia:gender:"))
async def leia_gender_pick(callback: CallbackQuery) -> None:
    await safe_callback_answer(callback)
    key = callback.data.removeprefix("leia:gender:")
    value = _GENDER_VALUES.get(key)
    if not value or callback.from_user is None:
        return
    service = OnboardingService()
    step = await service.get_current_step_key(callback.from_user)
    if step != "gender":
        await callback.message.answer(
            "Этот шаг уже пройден. Если нужно поменять пол — открой 👤 Профиль → ✏️ Изменить."
        )
        return
    reply, _, completed = await service.handle_answer(callback.from_user, value)
    if not reply:
        return
    if completed:
        await callback.message.answer(reply)
        await complete_onboarding_flow(callback.message, callback.from_user.id)
        return
    next_step = await service.get_current_step_key(callback.from_user)
    await callback.message.answer(reply, reply_markup=onboarding_markup_for_step(next_step or ""))


@router.callback_query(F.data == "leia:edit_profile")
async def leia_edit_profile(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    await callback.message.answer(
        "✏️ Что изменить в профиле?",
        reply_markup=inline_leia_edit_menu(),
    )


@router.callback_query(F.data.startswith("leia:edit:"))
async def leia_edit_field_start(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    field_key = callback.data.removeprefix("leia:edit:")
    if field_key not in PROFILE_EDIT_FIELDS:
        return
    if field_key == "gender":
        await state.clear()
        await callback.message.answer(
            ONBOARDING_PROMPTS["gender"],
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👩 Женский", callback_data="leia:set_gender:female"
                        ),
                        InlineKeyboardButton(
                            text="👨 Мужской", callback_data="leia:set_gender:male"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text="⏭ Не указывать", callback_data="leia:set_gender:skip"
                        )
                    ],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="leia:edit_profile")],
                ]
            ),
        )
        return
    await state.set_state(BotStates.waiting_profile_field)
    await state.update_data(profile_field=field_key, profile_edit_source="leia")
    prompt = ONBOARDING_PROMPTS.get(field_key) or ProfileService().prompt_for_field(field_key, "ru")
    await callback.message.answer(
        prompt,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="leia:edit_profile")],
            ]
        ),
    )


@router.callback_query(F.data.startswith("leia:set_gender:"))
async def leia_set_gender(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    key = callback.data.removeprefix("leia:set_gender:")
    value = _GENDER_VALUES.get(key)
    if not value or callback.from_user is None:
        return
    result = await ProfileService().update_field(callback.from_user.id, "gender", value)
    await state.clear()
    await callback.message.answer(result or "✅ Пол обновлён")
    await show_leia_profile(callback.message, telegram_id=callback.from_user.id)


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
        await message.answer(
            PAYMENT_LINK,
            reply_markup=inline_payment_button(
                flow.payment_url, amount_rub=flow.amount_rub
            ),
        )


async def _run_entitled_full(
    message: Message,
    *,
    user: User,
    product_id: str,
    extra_context: str = "",
    state: FSMContext | None = None,
    telegram_id: int | None = None,
) -> None:
    service = ProductService()
    # callback.message.from_user is the bot — always prefer explicit telegram_id.
    tid = telegram_id
    if tid is None and message.from_user is not None:
        tid = message.from_user.id
    if tid is None:
        tid = message.chat.id
    try:
        if product_id == "tarot_spread":
            question = extra_context or "Мой вопрос"

            async def _gen_tarot():
                return await service.generate_tarot_spread(
                    user.id,
                    question,
                    level="full",
                    use_entitlement=True,
                )

            result = await run_busy_job(
                message,
                _gen_tarot,
                loading_text=ENTITLED_FULL,
                progress_text="🃏 Карты уже выпали — собираю толкование…",
                telegram_id=tid,
                label=f"full:{product_id}",
            )
            if result is None:
                return
            text, cards = result
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

        text = await run_busy_job(
            message,
            lambda: service.generate_full(
                user.id, product_id, extra_context=extra_context, use_entitlement=True
            ),
            loading_text=ENTITLED_FULL,
            progress_text="✨ Ещё собираю полный разбор… почти готово",
            telegram_id=tid,
            label=f"full:{product_id}",
        )
        if text is None:
            return
        if not (text or "").strip():
            await message.answer("Не получилось сейчас — попробуй чуть позже.")
            return
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
    if callback.from_user is None or callback.message is None:
        return
    service = OnboardingService()
    # Old «Соглашаюсь» after reset: recreate user first.
    await service.start_or_resume(callback.from_user)
    prompt, _ = await service.advance_from_consent(callback.from_user)
    if not prompt:
        step = await service.get_current_step_key(callback.from_user) or "legal_consent"
        prompt = service.prompt_for_step(step)
    next_step = await service.get_current_step_key(callback.from_user) or "name"
    await callback.message.answer(prompt, reply_markup=onboarding_markup_for_step(next_step))


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
    if user is None or not user.is_onboarded:
        await _ensure_onboarded_or_restart(callback.message, telegram_id)
        return
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
        elif flow.payment_url:
            await callback.message.answer(
                PACKAGE_PAYMENT,
                reply_markup=inline_payment_button(
                    flow.payment_url, amount_rub=flow.amount_rub, package=True
                ),
            )
        else:
            await callback.message.answer("Оплата временно недоступна.")
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
    mini_used = False
    if user:
        access_label = await _product_access_label(user.id, product_id)
        has_plan = await ent.has_any_plan(user.id)
        mini_used = await ProductService().has_mini(user.id, product_id)
    await callback_leia_scene(
        callback,
        format_product_pitch_rich(
            product_id, access_label=access_label, has_plan=has_plan
        ),
        reply_markup=inline_product_actions(
            product_id, access_label=access_label, mini_used=mini_used
        ),
        image_key=product_id,
    )


@router.callback_query(F.data.startswith("leia:mini_used:"))
async def leia_mini_used(callback: CallbackQuery) -> None:
    await safe_callback_answer(
        callback,
        "Мини-версия уже была — открой полную расшифровку 🔓",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("leia:history:"))
async def leia_history(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    if callback.message is None:
        return
    try:
        page = int(callback.data.removeprefix("leia:history:"))
    except ValueError:
        page = 0
    await show_leia_history(
        callback.message,
        page=page,
        telegram_id=callback.from_user.id,
    )


@router.callback_query(F.data.startswith("leia:hist:"))
async def leia_history_open(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    if callback.message is None:
        return
    usage_id = callback.data.removeprefix("leia:hist:")
    user = await _db_user(callback.from_user.id)
    if user is None:
        return
    row = await ProductService().get_usage(user.id, usage_id)
    if row is None or not (row.content_preview or "").strip():
        await callback.message.answer("Этот разбор уже недоступен.")
        return
    product = PRODUCTS.get(row.product_id)
    title = f"{product.emoji} {product.title}" if product else "Разбор"
    level = "мини" if row.level == "mini" else "полная"
    when = row.created_at.strftime("%d.%m.%Y %H:%M") if row.created_at else ""
    header = f"### 📜 {title}\n\n_{level} · {when}_\n\n"
    body = f"{header}{row.content_preview}"
    await state.update_data(
        last_reading_text=row.content_preview[:4000],
        last_product_id=row.product_id,
    )
    await answer_rich_message(
        callback.message,
        body,
        reply_markup=inline_history_item(),
    )


@router.callback_query(F.data.startswith("leia:launch:"))
async def leia_launch(callback: CallbackQuery, state: FSMContext) -> None:
    if await refuse_if_busy_callback(callback):
        return
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
        mini_used = await ProductService().has_mini(user.id, product_id)
        await callback_leia_scene(
            callback,
            format_product_pitch_rich(
                product_id, access_label=access_label, has_plan=has_plan
            ),
            reply_markup=inline_product_actions(
                product_id, access_label=access_label, mini_used=mini_used
            ),
            image_key=product_id,
        )
        return

    if product_id == "love":
        await state.set_state(BotStates.waiting_partner_birth_date)
        await state.update_data(product_id=product_id, mode="full_entitled")
        await callback.message.answer(PRODUCTS["love"].mini_hint)
        return
    if product_id == "chat":
        await _start_chat_collect(callback.message, state, product_id=product_id, mode="full_entitled")
        return
    if product_id in ("question", "tarot_spread"):
        await state.set_state(BotStates.waiting_product_question)
        await state.update_data(product_id=product_id, mode="full_entitled")
        await callback.message.answer(PRODUCTS[product_id].mini_hint)
        return

    await _run_entitled_full(
        callback.message,
        user=user,
        product_id=product_id,
        state=state,
        telegram_id=callback.from_user.id,
    )


@router.callback_query(F.data.startswith("leia:mini:"))
async def leia_mini(callback: CallbackQuery, state: FSMContext) -> None:
    if await refuse_if_busy_callback(callback):
        return
    product_id = callback.data.removeprefix("leia:mini:")
    product = PRODUCTS.get(product_id)
    if product is None:
        await safe_callback_answer(callback)
        return

    user = await _db_user(callback.from_user.id)
    if user is None:
        await safe_callback_answer(callback)
        return
    if await ProductService().has_mini(user.id, product_id):
        await safe_callback_answer(
            callback,
            "Мини-версия уже была — открой полную расшифровку 🔓",
            show_alert=True,
        )
        return

    await safe_callback_answer(callback)

    if product_id == "love":
        await state.set_state(BotStates.waiting_partner_birth_date)
        await state.update_data(product_id=product_id, mode="mini")
        await callback.message.answer(product.mini_hint)
        return
    if product_id == "chat":
        await _start_chat_collect(callback.message, state, product_id=product_id, mode="mini")
        return
    if product_id in ("question", "tarot_spread"):
        await state.set_state(BotStates.waiting_product_question)
        await state.update_data(product_id=product_id, mode="mini")
        await callback.message.answer(product.mini_hint)
        return

    try:
        text = await run_busy_job(
            callback.message,
            lambda: ProductService().generate_mini(user.id, product_id),
            loading_text=PRODUCT_LOADING,
            progress_text="✨ Ещё смотрю числа… почти готово",
            telegram_id=callback.from_user.id,
            label=f"mini:{product_id}",
        )
        if text is None:
            return
        if not (text or "").strip():
            await callback.message.answer(
                "Не получилось собрать мини-разбор — попробуй ещё раз чуть позже."
            )
            return
        access_label = await _product_access_label(user.id, product_id)
        await answer_rich_message(
            callback.message, text, reply_markup=inline_after_mini(product_id, access_label=access_label)
        )
    except Exception:
        logger.exception("Mini product failed")
        await callback.message.answer("Не получилось сейчас — попробуй чуть позже.")


@router.callback_query(F.data.startswith("leia:full:"))
async def leia_full_pay(callback: CallbackQuery, state: FSMContext) -> None:
    if await refuse_if_busy_callback(callback):
        return
    product_id = callback.data.removeprefix("leia:full:")
    product = PRODUCTS.get(product_id)
    if product is None:
        await safe_callback_answer(callback)
        return

    user = await _db_user(callback.from_user.id)
    if user is None:
        await safe_callback_answer(callback)
        return
    service = ProductService()
    existing = await service.latest_full_for_product(user.id, product_id)
    if existing and not await _product_entitled(user.id, product_id):
        # Already bought once — resend instead of a dead-end alert.
        await safe_callback_answer(callback, "Открываю твой полный разбор ✨")
        await _deliver_full_reading(
            callback.message, existing, state=state, product_id=product_id
        )
        return

    await safe_callback_answer(callback)
    entitled = await _product_entitled(user.id, product_id)

    if product_id == "love":
        await state.set_state(BotStates.waiting_partner_birth_date)
        await state.update_data(
            product_id=product_id,
            mode="full_entitled" if entitled else "full_pay",
        )
        await callback.message.answer(product.mini_hint)
        return
    if product_id == "chat":
        await _start_chat_collect(
            callback.message,
            state,
            product_id=product_id,
            mode="full_entitled" if entitled else "full_pay",
        )
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
        await _run_entitled_full(
            callback.message,
            user=user,
            product_id=product_id,
            state=state,
            telegram_id=callback.from_user.id,
        )
        return

    try:
        flow = await run_busy_job(
            callback.message,
            lambda: service.create_full_payment(user, product_id),
            loading_text="💳 Готовлю полный разбор…",
            progress_text="✨ Ещё собираю расшифровку… обычно до минуты",
            telegram_id=callback.from_user.id,
            label=f"pay:{product_id}",
        )
        if flow is None:
            return
        await _deliver_payment_flow(callback.message, flow, state=state)
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

    if await refuse_if_busy_message(message):
        return

    chat = LeiaChatService()
    if not reading and user and await chat.has_open_chat(user.id):
        try:
            reply = await run_busy_job(
                message,
                lambda: chat.answer_freeform(user.id, name, question),
                loading_text=PAID_CHAT_LOADING,
                progress_text="💬 Ещё думаю над ответом…",
                label="chat",
            )
            if reply is None:
                return
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

    try:
        answer = await run_busy_job(
            message,
            lambda: ReadingFollowupService().answer(
                reading_excerpt=reading,
                question=question,
                user_name=name,
                user_id=user.id if user else None,
            ),
            loading_text="💬 Думаю над твоим вопросом…",
            progress_text="✨ Ещё собираю ответ…",
            label="followup",
        )
        if answer is None:
            return
        await answer_rich_message(message, answer, reply_markup=inline_after_full_reading())
    except Exception:
        logger.exception("Reading followup failed")
        await message.answer("Не получилось ответить сейчас — попробуй переформулировать вопрос.")


async def _start_chat_collect(
    message: Message,
    state: FSMContext,
    *,
    product_id: str,
    mode: str,
) -> None:
    await state.set_state(BotStates.waiting_chat_collect)
    await state.update_data(product_id=product_id, mode=mode, chat_chunks=[])
    await message.answer(
        PRODUCTS["chat"].mini_hint,
        reply_markup=inline_chat_collect(),
    )


def _extract_chat_chunk(message: Message) -> str | None:
    text = (message.text or message.caption or "").strip()
    if not text:
        return None
    origin = ""
    if message.forward_from:
        name = message.forward_from.full_name or message.forward_from.username or "собеседник"
        origin = f"[от {name}] "
    elif getattr(message, "forward_origin", None) is not None:
        origin = "[переслано] "
    return f"{origin}{text}"


@router.message(BotStates.waiting_chat_collect)
async def chat_collect(message: Message, state: FSMContext) -> None:
    if await refuse_if_busy_message(message):
        return
    raw = (message.text or "").strip().lower()
    if raw in {"готово", "готово.", "готово!", "done"}:
        await _finish_chat_collect(message, state)
        return
    chunk = _extract_chat_chunk(message)
    if not chunk:
        await message.answer(
            "Пришли текст или перешли сообщения. Когда хватит — нажми «Готово».",
            reply_markup=inline_chat_collect(),
        )
        return
    data = await state.get_data()
    chunks = list(data.get("chat_chunks") or [])
    chunks.append(chunk)
    # лимит ~12k символов суммарно
    joined = "\n".join(chunks)
    if len(joined) > 12000:
        chunks = [joined[-12000:]]
    await state.update_data(chat_chunks=chunks)
    await message.answer(
        f"Приняла ({len(chunks)} фрагм.). Ещё или «Готово».",
        reply_markup=inline_chat_collect(),
    )


@router.callback_query(F.data == "leia:chat_done")
async def chat_done(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await _finish_chat_collect(callback.message, state)


async def _finish_chat_collect(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    chunks = list(data.get("chat_chunks") or [])
    if not chunks:
        await message.answer(
            "Пока пусто — пришли хотя бы несколько реплик.",
            reply_markup=inline_chat_collect(),
        )
        return
    await state.set_state(BotStates.waiting_chat_role)
    await state.update_data(chat_text="\n".join(chunks))
    await message.answer(
        "Кто ты в этой переписке? Так Лея не перепутает роли.",
        reply_markup=inline_chat_role(),
    )


@router.callback_query(F.data.startswith("leia:chat_role:"))
async def chat_role_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    if await refuse_if_busy_callback(callback):
        return
    which = callback.data.removeprefix("leia:chat_role:")
    role = "я (пользователь бота)" if which == "me" else "партнёр; пользователь бота = вторая сторона"

    data = await state.get_data()
    product_id = data.get("product_id", "chat")
    mode = data.get("mode", "mini")
    chat_text = str(data.get("chat_text") or "").strip()
    if len(chat_text) < 20:
        await safe_callback_answer(callback, "Переписки мало — добавь ещё", show_alert=True)
        await state.set_state(BotStates.waiting_chat_collect)
        return

    await safe_callback_answer(callback)
    user = await _db_user(callback.from_user.id)
    if user is None:
        await state.clear()
        return

    packed = ProductService.pack_chat_context(role=role, text=chat_text)

    if mode == "full_pay":
        await state.clear()
        try:
            flow = await run_busy_job(
                callback.message,
                lambda: ProductService().create_full_payment(
                    user, product_id, extra_context=packed
                ),
                loading_text="💳 Готовлю полный разбор…",
                progress_text="✨ Читаю подтекст…",
                telegram_id=callback.from_user.id,
                label=f"pay:{product_id}",
            )
            if flow is None:
                return
            await _deliver_payment_flow(callback.message, flow, state=state)
        except Exception:
            await callback.message.answer("Оплата временно недоступна.")
        return

    if mode == "full_entitled":
        await _run_entitled_full(
            callback.message,
            user=user,
            product_id=product_id,
            extra_context=packed,
            state=state,
            telegram_id=callback.from_user.id,
        )
        await state.clear()
        return

    await state.clear()
    text = await run_busy_job(
        callback.message,
        lambda: ProductService().generate_mini(user.id, product_id, extra_context=packed),
        loading_text=PRODUCT_LOADING,
        progress_text="💬 Читаю переписку…",
        telegram_id=callback.from_user.id,
        label=f"mini:{product_id}",
    )
    if text is None:
        return
    if not (text or "").strip():
        await callback.message.answer("Не получилось разобрать — попробуй ещё раз.")
        return
    access_label = await _product_access_label(user.id, product_id)
    await answer_rich_message(
        callback.message, text, reply_markup=inline_after_mini(product_id, access_label=access_label)
    )


@router.message(BotStates.waiting_partner_birth_date)
async def partner_birth_date(message: Message, state: FSMContext) -> None:
    if await refuse_if_busy_message(message):
        return
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
            flow = await run_busy_job(
                message,
                lambda: ProductService().create_full_payment(
                    user, product_id, extra_context=partner_info
                ),
                loading_text="💳 Готовлю полный разбор…",
                progress_text="✨ Ещё собираю расшифровку…",
                label=f"pay:{product_id}",
            )
            if flow is None:
                return
            await _deliver_payment_flow(message, flow, state=state)
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
    text = await run_busy_job(
        message,
        lambda: ProductService().generate_mini(
            user.id, product_id, extra_context=partner_info
        ),
        loading_text=PRODUCT_LOADING,
        progress_text="💞 Ещё смотрю совместимость…",
        label=f"mini:{product_id}",
    )
    if text is None:
        return
    access_label = await _product_access_label(user.id, product_id)
    await answer_rich_message(
        message, text, reply_markup=inline_after_mini(product_id, access_label=access_label)
    )


@router.message(BotStates.waiting_product_question)
async def product_question(message: Message, state: FSMContext) -> None:
    if await refuse_if_busy_message(message):
        return
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

    from app.services.dialog_log import log_dialog_message
    from app.database.models import MessageRole

    await log_dialog_message(
        user.id,
        MessageRole.USER.value,
        question,
        meta={"source": "product_question", "product_id": product_id, "mode": mode},
    )

    if mode == "full_pay":
        await state.clear()
        try:
            flow = await run_busy_job(
                message,
                lambda: ProductService().create_full_payment(
                    user, product_id, extra_context=question
                ),
                loading_text="💳 Готовлю полный разбор…",
                progress_text="✨ Ещё собираю расшифровку…",
                label=f"pay:{product_id}",
            )
            if flow is None:
                return
            await _deliver_payment_flow(message, flow, state=state)
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
    service = ProductService()
    if product_id == "tarot_spread":
        result = await run_busy_job(
            message,
            lambda: service.generate_tarot_spread(user.id, question, level="mini"),
            loading_text=PRODUCT_LOADING,
            progress_text="🃏 Карты выпали — пишу толкование…",
            label="mini:tarot_spread",
        )
        if result is None:
            return
        text, cards = result
        await _deliver_tarot_spread(
            message,
            question=question,
            text=text,
            cards=cards,
            product_id=product_id,
            level="mini",
            state=state,
        )
        return
    text = await run_busy_job(
        message,
        lambda: service.generate_mini(user.id, product_id, extra_context=question),
        loading_text=PRODUCT_LOADING,
        progress_text="✨ Ещё думаю над ответом…",
        label=f"mini:{product_id}",
    )
    if text is None:
        return
    access_label = await _product_access_label(user.id, product_id)
    await answer_rich_message(
        message, text, reply_markup=inline_after_mini(product_id, access_label=access_label)
    )
    if (text or "").strip():
        await _store_reading_state(state, text, product_id)


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
    if await refuse_if_busy_callback(callback):
        return
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
            reply_markup=inline_product_actions(
                product_id, access_label=access_label, mini_used=True
            ),
            image_key=product_id,
        )
        return
    try:
        text = await run_busy_job(
            callback.message,
            lambda: service.generate_mini(user.id, product_id),
            loading_text=PRODUCT_LOADING,
            progress_text="✨ Ещё собираю мини-разбор…",
            telegram_id=callback.from_user.id,
            label=f"mini:{product_id}",
        )
        if text is None:
            return
        if not (text or "").strip():
            await callback.message.answer(
                "Не получилось собрать мини-разбор — попробуй ещё раз чуть позже."
            )
            return
        access_label = await _product_access_label(user.id, product_id)
        await answer_leia_rich(
            callback.message,
            text,
            reply_markup=inline_after_mini(product_id, access_label=access_label),
            image_key=product_id,
        )
    except Exception:
        logger.exception("Funnel mini failed for %s", product_id)
        await callback.message.answer("Не получилось сейчас — попробуй из меню чуть позже.")
