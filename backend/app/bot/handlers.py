import asyncio
import logging
import traceback
from decimal import Decimal

from aiogram import Dispatcher, F, Router
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, User as TelegramUser
from sqlalchemy import select

from app.bot.content import info_panel_text, support_url
from app.bot.audio_media import send_voice_from_url
from app.bot.cards_media import send_card_with_caption, send_tarot_reading_rich
from app.bot.media import send_photo_from_url
from app.bot.formatting import to_telegram_html
from app.bot.rich_messages import answer_rich_message, present_rich_panel, truncate_text
from app.core.config import get_settings
from app.bot.helpers import clear_processing_placeholder, safe_callback_answer, safe_edit, send_processing_placeholder
from app.bot.i18n import all_menu_texts, main_menu_text, menu_actions, normalize_language, reading_label, t
from app.bot.i18n_extra import ONBOARDING_CHOICE_STEPS
from app.bot.keyboards import (
    MENU_ACTIONS,
    inline_billing_menu,
    inline_history_menu,
    inline_info_menu,
    inline_language_menu,
    inline_main_menu,
    inline_memory_detail_menu,
    inline_memory_empty_menu,
    inline_memory_list_menu,
    inline_payment_menu,
    inline_photo_mode_menu,
    inline_profile_edit_menu,
    inline_profile_menu,
    inline_reading_prompt,
    inline_readings_menu,
    inline_referral_menu,
    inline_referral_list_menu,
    inline_referral_stats_menu,
    inline_settings_menu,
    inline_spending_menu,
    inline_withdraw_wallet_menu,
    is_balance_button,
    is_home_button,
    main_menu,
    onboarding_keyboard,
    profile_field_keyboard,
    READINGS_MENU_TEXT,
)
from app.bot.states import BotStates
from app.bot.streaming import chat_action_loop, stream_to_message, typing_loop
from app.database.models import Subscription, User, UserSettings
from app.database.session import AsyncSessionLocal
from app.services.ai.orchestrator import AIOrchestrator
from app.services.analytics.tracker import track_event
from app.services.billing.limits import (
    FREE_CHAT_MESSAGES_PER_MONTH,
    FREE_READINGS_PER_MONTH,
    can_use_premium_voice,
    free_messages_left,
)
from app.services.billing.tokens import format_balance
from platega.exceptions import PlategaAPIError

from app.services.billing.service import BillingService
from app.services.memory.panel import MemoryPanelService
from app.services.onboarding.service import ONBOARDING_STEPS, OnboardingService
from app.services.profile.service import ProfileService
from app.services.referrals.service import (
    MIN_WITHDRAWAL_RUB,
    ReferralService,
    is_valid_trc20_wallet,
    parse_withdrawal_amount,
)
from app.services.settings.service import SettingsService
from app.services.tarot.service import READING_TYPES, TarotService
from app.services.vision.service import VisionService
from app.services.voice.service import VoiceService
from app.services.media.telegram_audio import store_telegram_voice
from app.bot.feature_handlers import (
    handle_bracelet_query,
    handle_rune_question,
    handle_stone_query,
    handle_zen_question,
    router as feature_router,
)

router = Router()
logger = logging.getLogger(__name__)

# FSM modes started from inline menus — only active until user answers or cancels.
_FEATURE_WAIT_STATES = frozenset(
    {
        BotStates.waiting_reading_question.state,
        BotStates.waiting_zen_question.state,
        BotStates.waiting_rune_question.state,
        BotStates.waiting_stone_query.state,
        BotStates.waiting_bracelet_query.state,
    }
)

# Typing these while in a feature prompt returns to free chat (state cleared).
_CHAT_ESCAPE_WORDS = frozenset(
    {
        "отмена",
        "cancel",
        "назад",
        "back",
        "стоп",
        "stop",
        "меню",
        "menu",
        "exit",
        "выход",
    }
)


def _admin_telegram_ids() -> set[int]:
    raw = get_settings().telegram_admin_ids
    return {int(part.strip()) for part in raw.split(",") if part.strip().isdigit()}


def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)

    def _log_failure(done_task: asyncio.Task) -> None:
        try:
            done_task.result()
        except Exception:
            logger.exception("Background bot task failed")

    task.add_done_callback(_log_failure)


async def _track(user_id: str | None, event: str, payload: dict | None = None) -> None:
    _fire_and_forget(track_event(event, user_id=user_id, payload=payload))


async def _get_user_id(telegram_id: int) -> str | None:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        return user.id if user else None


async def _user_language(telegram_id: int) -> str:
    return await SettingsService().get_ui_language(telegram_id)


async def _user_main_menu(telegram_id: int):
    balance = await BillingService().get_balance_label(telegram_id)
    lang = await _user_language(telegram_id)
    return main_menu(balance, lang)


async def _go_home(message: Message, state: FSMContext) -> None:
    await state.clear()
    telegram_id = message.from_user.id
    menu_text, menu_markup = await _main_menu_inline(telegram_id)
    await present_rich_panel(message, menu_text, reply_markup=menu_markup)


async def _main_menu_inline(telegram_id: int):
    lang = await _user_language(telegram_id)
    status = await BillingService().home_status_text(telegram_id)
    body = main_menu_text(lang)
    text = f"{status}\n\n---\n\n{body}" if status else body
    return text, inline_main_menu(lang)


async def _open_billing(message: Message, *, edit_message: Message | None = None) -> None:
    lang = await _user_language(message.from_user.id)
    text = await BillingService().panel_text(message.from_user.id)
    markup = inline_billing_menu(lang)
    await present_rich_panel(message, text, reply_markup=markup, edit_message=edit_message)


async def _readings_menu_text(telegram_id: int) -> str:
    lang = await _user_language(telegram_id)
    left = await TarotService().readings_left_today(telegram_id)
    return (
        f"{t('readings_menu_text', lang)}\n\n"
        f"{t('readings_left_month', lang, left=left, limit=FREE_READINGS_PER_MONTH)}"
    )


async def _show_reading_history(
    message: Message,
    telegram_id: int,
    page: int = 0,
    *,
    edit_message: Message | None = None,
) -> None:
    lang = await _user_language(telegram_id)
    tarot = TarotService()
    text, readings, page, total_pages = await tarot.history_page(telegram_id, page, lang=lang)
    markup = inline_history_menu(readings, page, total_pages, lang) if readings else None
    if edit_message is not None:
        await safe_edit(edit_message, text, markup, parse_mode=None)
    else:
        await message.answer(text, reply_markup=markup, parse_mode=None)


async def _show_memory_list(
    message: Message,
    telegram_id: int,
    page: int = 0,
    *,
    edit_message: Message | None = None,
) -> None:
    service = MemoryPanelService()
    text, memories, page, total_pages = await service.list_page(telegram_id, page)
    if memories:
        markup = inline_memory_list_menu(memories, page, total_pages, lang)
    else:
        markup = inline_memory_empty_menu(lang)
    if edit_message is not None:
        await safe_edit(edit_message, text, markup, parse_mode=None)
    else:
        await message.answer(text, reply_markup=markup, parse_mode=None)


async def _open_referrals(
    message: Message,
    *,
    edit_message: Message | None = None,
    telegram_id: int | None = None,
) -> None:
    actor_id = telegram_id or (message.from_user.id if message.from_user else None)
    if actor_id is None:
        return
    lang = await _user_language(actor_id)
    bot_user = await message.bot.get_me()
    username = bot_user.username
    if not username:
        text = t("error_generic", lang)
        if edit_message is not None:
            await safe_edit(edit_message, text)
        else:
            await message.answer(text)
        return
    text = await ReferralService().panel_text(actor_id, bot_username=username)
    share_link = ReferralService().build_referral_link(username, actor_id)
    markup = inline_referral_menu(share_link=share_link, lang=lang)
    await present_rich_panel(message, text, reply_markup=markup, edit_message=edit_message)


async def _with_typing(message: Message, coro):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    return await coro


async def _answer_formatted(message: Message, text: str, *, prefix: str = "") -> None:
    await answer_rich_message(message, f"{prefix}{text}")


async def _generate_with_typing(message: Message, coro):
    stop = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(message.bot, message.chat.id, stop))
    try:
        return await coro
    finally:
        stop.set()
        await typing_task


async def _send_daily_card(message: Message, telegram_id: int) -> None:
    lang = await _user_language(message.from_user.id)
    tarot = TarotService()
    interpretation, card = await _generate_with_typing(
        message,
        tarot.daily_card_for_telegram(telegram_id),
    )
    if card is None:
        await message.answer(interpretation)
        return

    menu_markup = await _user_main_menu(telegram_id)
    interpretation_plain = interpretation.strip()
    interpretation_html = to_telegram_html(interpretation_plain)

    if card and await send_card_with_caption(
        message,
        card,
        caption_html=interpretation_html,
        caption_plain=interpretation_plain,
        reply_markup=menu_markup,
    ):
        await tarot.record_daily_card_context(
            telegram_id,
            interpretation_plain,
            card_name=str(card.get("name", "")),
        )
        return

    html = truncate_text(to_telegram_html(interpretation_plain))
    try:
        await message.answer(html, parse_mode=ParseMode.HTML, reply_markup=menu_markup)
    except Exception:
        await message.answer(
            truncate_text(interpretation_plain),
            parse_mode=None,
            reply_markup=menu_markup,
        )
    await tarot.record_daily_card_context(
        telegram_id,
        interpretation_plain,
        card_name=str(card.get("name", "")) if card else "",
    )


async def _handle_reading_question(message: Message, state: FSMContext, question: str) -> None:
    lang = await _user_language(message.from_user.id)
    data = await state.get_data()
    reading_type = data.get("reading_type", "past_present_future")

    tarot = TarotService()
    ok, limit_error = await tarot.ensure_can_read_today(message.from_user.id)
    if not ok:
        await state.clear()
        await message.answer(limit_error, reply_markup=await _user_main_menu(message.from_user.id))
        return

    await state.clear()

    user_id = await _get_user_id(message.from_user.id)
    if user_id is None:
        await message.answer(t("error_need_start", lang))
        return

    orchestrator = AIOrchestrator()
    label = reading_label(reading_type, lang)
    cards = tarot.draw_cards(READING_TYPES.get(reading_type, 3))

    user_db_id, messages, error, user_message_id, billing_mode = await orchestrator.prepare_tarot_reading(
        message.from_user, question, cards, reading_type
    )
    if error:
        await message.answer(error)
        return

    if billing_mode == "balance":
        await message.answer(t("error_free_messages_ended", lang))

    interpretation = await _generate_with_typing(
        message,
        orchestrator.generate_chat(messages or []),
    )
    if not interpretation or "cannot fulfill" in interpretation.lower():
        interpretation = tarot.interpret_locally(question, cards, lang)

    from app.bot.rich_layouts import format_tarot_reading_rich

    menu_markup = await _user_main_menu(message.from_user.id)
    await send_tarot_reading_rich(
        message,
        label=label,
        question=question,
        reading_type=reading_type,
        cards=cards,
        interpretation=interpretation,
        lang=lang,
        reply_markup=menu_markup,
    )

    stored_answer = format_tarot_reading_rich(
        label=label,
        question=question,
        cards=cards,
        reading_type=reading_type,
        interpretation=interpretation,
        lang=lang,
        include_collage=False,
    )
    usage = await orchestrator.complete_chat(
        user_db_id or user_id,
        question,
        stored_answer,
        user_message_id=user_message_id,
        context_messages=messages,
        feature="tarot_reading",
        billing_mode=billing_mode,
    )
    await _notify_billing(
        message,
        billing_mode,
        usage,
    )
    await tarot.create_reading(
        user_id,
        reading_type,
        question,
        cards=cards,
        interpretation=interpretation,
    )
    await _track(user_id, "bot.reading", {"reading_type": reading_type})


async def _notify_billing(
    message: Message,
    billing_mode: str,
    usage: dict,
    *,
    reply_markup=None,
    telegram_id: int | None = None,
    lang: str | None = None,
) -> bool:
    user_telegram_id = telegram_id or (message.from_user.id if message.from_user else 0)
    if lang is None:
        lang = await _user_language(user_telegram_id)
    charged = Decimal(str(usage.get("charged_rub", "0")))
    image_charged = Decimal(str(usage.get("image_charged_rub", "0")))
    if charged > 0:
        parts = [t("chat_charged", lang, charged=charged)]
        if image_charged > 0:
            parts.append(t("chat_charged_infographic", lang, amount=image_charged))
        parts.append(
            t("chat_balance_after", lang, balance=format_balance(usage.get("balance_after")))
        )
        if reply_markup is None:
            reply_markup = await _user_main_menu(user_telegram_id)
        await message.answer(" ".join(parts), reply_markup=reply_markup)
        return True
    if billing_mode == "free" and free_messages_left(
        (await _get_user_free_used(user_telegram_id))
    ) == 0:
        await message.answer(
            t("chat_last_free", lang, limit=FREE_CHAT_MESSAGES_PER_MONTH),
            reply_markup=reply_markup,
        )
        return True
    return False


async def _process_photo_request_safe(
    message: Message,
    state: FSMContext,
    *,
    file_id: str,
    mode: str,
    custom_text: str = "",
    telegram_user: TelegramUser | None = None,
) -> None:
    try:
        await _process_photo_request(
            message,
            state,
            file_id=file_id,
            mode=mode,
            custom_text=custom_text,
            telegram_user=telegram_user,
        )
    except asyncio.CancelledError:
        await _track(None, "bot.error", {"handler": "photo", "error": "cancelled"})
        lang = await _user_language(message.from_user.id if message.from_user else 0)
        try:
            await message.answer(t("photo_processing_interrupted", lang))
        except Exception:
            pass
    except Exception as exc:
        await _track(None, "bot.error", {"handler": "photo", "error": str(exc)})
        lang = await _user_language(message.from_user.id if message.from_user else 0)
        await message.answer(t("error_photo_process", lang, detail=exc))


async def _process_photo_request(
    message: Message,
    state: FSMContext,
    *,
    file_id: str,
    mode: str,
    custom_text: str = "",
    telegram_user: TelegramUser | None = None,
) -> None:
    await state.clear()
    actor = telegram_user or message.from_user
    lang = await _user_language(actor.id if actor else 0)
    if actor is None:
        await message.answer(t("error_telegram_profile", lang))
        return

    user_id = await _get_user_id(actor.id)
    if user_id is None:
        await message.answer(t("error_need_start", lang))
        return

    waiting_msg = await send_processing_placeholder(message, kind="photo")

    action_stop = asyncio.Event()
    action_task = asyncio.create_task(
        typing_loop(message.bot, message.chat.id, action_stop)
    )

    async def on_analysis_complete(_interpretation: str) -> None:
        nonlocal action_task, action_stop
        action_stop.set()
        await action_task
        action_stop = asyncio.Event()
        action_task = asyncio.create_task(
            chat_action_loop(
                message.bot,
                message.chat.id,
                ChatAction.UPLOAD_PHOTO,
                action_stop,
            )
        )

    try:
        try:
            result, error = await VisionService().process_photo(
                message.bot,
                actor,
                file_id=file_id,
                mode=mode,
                custom_text=custom_text,
                on_analysis_complete=on_analysis_complete if mode in {"aura", "palm"} else None,
            )
        finally:
            action_stop.set()
            try:
                await action_task
            except asyncio.CancelledError:
                pass

        if error:
            await message.answer(error)
            return

        menu_markup = await _user_main_menu(actor.id)
        interpretation_plain = result.interpretation.strip()
        interpretation_html = to_telegram_html(interpretation_plain)

        if result.infographic_urls:
            sent = False
            for url in result.infographic_urls:
                if await send_photo_from_url(
                    message,
                    url,
                    caption=interpretation_html,
                    caption_plain=interpretation_plain,
                    parse_mode=ParseMode.HTML,
                    reply_markup=menu_markup,
                ):
                    sent = True
                    break
            if not sent:
                await message.answer(
                    interpretation_html,
                    parse_mode=ParseMode.HTML,
                    reply_markup=menu_markup,
                )
                await message.answer(
                    t("photo_infographic_send_failed", lang),
                    reply_markup=menu_markup,
                )
        else:
            await message.answer(
                interpretation_html,
                parse_mode=ParseMode.HTML,
                reply_markup=menu_markup,
            )

        await clear_processing_placeholder(waiting_msg)
        waiting_msg = None

        await _notify_billing(
            message,
            result.billing_mode,
            result.usage,
            reply_markup=await _user_main_menu(actor.id),
            telegram_id=actor.id,
        )
        await _track(user_id, "bot.vision", {"mode": mode, "feature": result.feature})
    finally:
        await clear_processing_placeholder(waiting_msg)


async def _get_user_free_used(telegram_id: int) -> int:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        return user.free_messages_used_month if user else 0


async def _chat_reply(message: Message, text: str, *, state: FSMContext | None = None) -> None:
    if state is not None:
        await state.clear()
    lang = await _user_language(message.from_user.id)
    orchestrator = AIOrchestrator()
    user_id, messages, error, user_message_id, billing_mode = await orchestrator.prepare_chat(
        message.from_user, text
    )
    if error:
        await message.answer(error)
        return

    if billing_mode == "balance":
        await message.answer(t("error_free_messages_ended", lang))

    try:
        answer = await stream_to_message(
            message,
            orchestrator.stream_chat(messages or []),
        )
    except Exception as exc:
        logger.exception("Chat reply failed")
        await _track(
            user_id,
            "bot.error",
            {"handler": "chat_reply", "error": str(exc), "traceback": traceback.format_exc()[-2000:]},
        )
        await message.answer(t("error_no_model_response", lang))
        return

    try:
        usage = await orchestrator.complete_chat(
            user_id or "",
            text,
            answer,
            user_message_id=user_message_id,
            context_messages=messages,
            billing_mode=billing_mode,
        )
        await _notify_billing(
            message,
            billing_mode,
            usage,
            reply_markup=await _user_main_menu(message.from_user.id),
        )
    except Exception as exc:
        logger.exception("Chat billing/memory failed")
        await _track(
            user_id,
            "bot.error",
            {"handler": "chat_complete", "error": str(exc), "traceback": traceback.format_exc()[-2000:]},
        )

    await _track(user_id, "bot.chat", {"telegram_id": message.from_user.id, "length": len(text)})


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, state: FSMContext) -> None:
    lang = await _user_language(message.from_user.id)
    await state.clear()
    try:
        service = OnboardingService()
        text, user_id, is_new = await service.start_or_resume(telegram_user=message.from_user)
        onboarded = await service.is_onboarded(message.from_user)

        if is_new and command.args and message.from_user:
            referrer_name = await ReferralService().attach_from_start_code(
                message.from_user.id,
                command.args,
            )
            if referrer_name:
                text = f"{text}\n\n{t('referral_invited', lang, name=referrer_name)}"

        if onboarded:
            await message.answer(text, reply_markup=await _user_main_menu(message.from_user.id))
            menu_text, menu_markup = await _main_menu_inline(message.from_user.id)
            await present_rich_panel(message, menu_text, reply_markup=menu_markup)
        else:
            step_key = await service.get_current_step_key(message.from_user) or ONBOARDING_STEPS[0][0]
            markup = onboarding_keyboard(step_key, lang)
            hint = ""
            if markup is None:
                hint = f"\n\n{t('onboarding_type_hint', lang)}"
            await message.answer(f"{text}{hint}", reply_markup=markup)

        await _track(
            user_id,
            "bot.user_created" if is_new else "bot.command_start",
            {"telegram_id": message.from_user.id if message.from_user else None},
        )
    except Exception as exc:
        await _track(None, "bot.error", {"handler": "start", "error": str(exc)})
        await message.answer(t("error_generic", lang))


@router.callback_query(F.data == "nav:noop")
async def nav_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("nav:back:"))
async def nav_back(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await safe_callback_answer(callback)
    target = callback.data.removeprefix("nav:back:")
    await state.clear()

    if target == "main":
        menu_text, menu_markup = await _main_menu_inline(callback.from_user.id)
        await present_rich_panel(
            callback.message, menu_text, reply_markup=menu_markup, edit_message=callback.message
        )
        return

    if target == "readings":
        await present_rich_panel(
            callback.message,
            await _readings_menu_text(callback.from_user.id),
            reply_markup=inline_readings_menu(lang),
            edit_message=callback.message,
        )
        return

    if target == "zen":
        lang = await _user_language(callback.from_user.id)
        from app.bot.keyboards import inline_zen_menu

        await present_rich_panel(
            callback.message,
            t("zen_menu_text", lang),
            reply_markup=inline_zen_menu(lang),
            edit_message=callback.message,
        )
        return

    if target == "energy":
        lang = await _user_language(callback.from_user.id)
        from app.bot.keyboards import inline_energy_menu

        await present_rich_panel(
            callback.message,
            t("energy_menu_text", lang),
            reply_markup=inline_energy_menu(lang),
            edit_message=callback.message,
        )
        return


@router.callback_query(F.data.startswith("hist:page:"))
async def history_page_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    page = int(callback.data.removeprefix("hist:page:"))
    await _show_reading_history(
        callback.message,
        callback.from_user.id,
        page,
        edit_message=callback.message,
    )


@router.callback_query(F.data.startswith("hist:open:"))
async def history_open(callback: CallbackQuery) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    reading_id = callback.data.removeprefix("hist:open:")
    tarot = TarotService()
    detail = await tarot.reading_detail_for_telegram(callback.from_user.id, reading_id)
    if detail is None:
        await callback.message.answer(t("error_reading_not_found", lang))
        return
    await callback.message.answer(detail, parse_mode=None)


async def _show_profile_edit(target: Message, telegram_id: int, *, prefix: str = "") -> None:
    lang = await _user_language(telegram_id)
    service = ProfileService()
    error, rows = await service.get_profile_summary(telegram_id)
    if error:
        await target.answer(error)
        return
    text = t("profile_edit_header", lang, prefix=prefix)
    await safe_edit(target, text, inline_profile_edit_menu(rows, lang))


@router.callback_query(F.data.startswith("set:prof:"))
async def profile_field_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    await state.clear()
    field_key = callback.data.removeprefix("set:prof:")
    service = ProfileService()
    prompt = service.prompt_for_field(field_key, lang)

    if field_key in ONBOARDING_CHOICE_STEPS:
        await safe_edit(
            callback.message,
            t("profile_pick_value", lang, prompt=prompt),
            profile_field_keyboard(field_key, lang),
        )
        return

    await state.set_state(BotStates.waiting_profile_field)
    await state.update_data(profile_field=field_key)
    await safe_edit(
        callback.message,
        t("profile_type_value", lang, prompt=prompt),
        profile_field_keyboard(field_key, lang),
    )


@router.callback_query(F.data.startswith("prof:pick:"))
async def profile_field_pick(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    payload = callback.data.removeprefix("prof:pick:")
    field_key, _, value = payload.partition(":")
    if not field_key or not value:
        return

    if field_key == "main_concern" and value.lower() in {
        "другое",
        t("mem_type_other", lang).lower(),
        t("mem_type_other", "en").lower(),
    }:
        await state.set_state(BotStates.waiting_profile_field)
        await state.update_data(profile_field=field_key)
        await safe_edit(
            callback.message,
            t("profile_concern_other", lang),
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=t("btn_back", lang), callback_data="nav:profile_edit")]
                ]
            ),
        )
        return

    service = ProfileService()
    result = await service.update_field(callback.from_user.id, field_key, value)
    if result is None:
        await callback.message.answer(t("error_update_field", lang))
        return
    await _show_profile_edit(callback.message, callback.from_user.id, prefix=f"{result}\n\n")
    await _track(None, "bot.profile_edit", {"field": field_key})


@router.callback_query(F.data.startswith("mem:"))
async def memory_callback(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    parts = callback.data.split(":")
    if len(parts) < 3:
        await safe_callback_answer(callback)
        return

    action = parts[1]
    service = MemoryPanelService()

    if action == "page":
        page = int(parts[2])
        await safe_callback_answer(callback)
        await _show_memory_list(
            callback.message,
            callback.from_user.id,
            page,
            edit_message=callback.message,
        )
        await _track(None, "bot.memory", {"action": "page", "page": page})
        return

    if action == "open" and len(parts) >= 4:
        memory_id, page = parts[2], int(parts[3])
        text = await service.detail_text(callback.from_user.id, memory_id)
        if text is None:
            await safe_callback_answer(callback, t("memory_not_found", lang), show_alert=True)
            return
        await safe_callback_answer(callback)
        await safe_edit(
            callback.message,
            text,
            inline_memory_detail_menu(memory_id, page, lang),
            parse_mode=None,
        )
        await _track(None, "bot.memory", {"action": "open", "memory_id": memory_id})
        return

    if action == "del" and len(parts) >= 4:
        memory_id, page = parts[2], int(parts[3])
        deleted = await service.deactivate(callback.from_user.id, memory_id)
        await safe_callback_answer(
            callback,
            t("memory_deleted", lang) if deleted else t("memory_not_found", lang),
            show_alert=not deleted,
        )
        if deleted:
            await _track(None, "bot.memory", {"action": "delete", "memory_id": memory_id})
        await _show_memory_list(
            callback.message,
            callback.from_user.id,
            page,
            edit_message=callback.message,
        )
        return

    if action == "add":
        page = int(parts[2])
        await safe_callback_answer(callback)
        await state.set_state(BotStates.waiting_memory_add)
        await state.update_data(memory_return_page=page)
        await callback.message.answer(t("memory_add_prompt", lang))
        await _track(None, "bot.memory", {"action": "add_start"})
        return

    await safe_callback_answer(callback)


@router.callback_query(F.data.startswith("set:"))
async def settings_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    service = SettingsService()
    action = callback.data.removeprefix("set:")

    if action == "timezone":
        text = await service.cycle_timezone(callback.from_user.id)
    elif action == "toggle:daily":
        text = await service.toggle_daily_card(callback.from_user.id)
    elif action == "toggle:proactive":
        text = await service.toggle_proactive(callback.from_user.id)
    elif action.startswith("lang:"):
        lang = action.removeprefix("lang:")
        text = await service.set_ui_language(callback.from_user.id, lang)
        await present_rich_panel(
            callback.message,
            text,
            reply_markup=await _user_main_menu(callback.from_user.id),
        )
        lang = await service.get_ui_language(callback.from_user.id)
        await present_rich_panel(
            callback.message,
            t("choose_language", lang),
            reply_markup=inline_language_menu(lang),
            edit_message=callback.message,
        )
        await _track(None, "bot.settings", {"action": "language", "lang": lang})
        return
    else:
        text = await service.get_panel_text(callback.from_user.id)

    lang = await service.get_ui_language(callback.from_user.id)
    await present_rich_panel(
        callback.message, text, reply_markup=inline_settings_menu(lang), edit_message=callback.message
    )
    await _track(None, "bot.settings", {"action": action})


@router.callback_query(F.data == "ref:share")
async def referral_share_callback(callback: CallbackQuery) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    bot_user = await callback.message.bot.get_me()
    link = ReferralService().build_referral_link(bot_user.username, callback.from_user.id)
    await callback.message.answer(
        t("referral_share_text", lang, link=link),
        reply_markup=inline_referral_menu(share_link=link, lang=lang),
    )


@router.callback_query(F.data == "ref:stats")
async def referral_stats_callback(callback: CallbackQuery) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    text = await ReferralService().stats_panel_text(callback.from_user.id)
    await present_rich_panel(
        callback.message, text, reply_markup=inline_referral_stats_menu(lang), edit_message=callback.message
    )
    await _track(None, "bot.referral", {"action": "stats"})


@router.callback_query(F.data.startswith("ref:list:"))
async def referral_list_callback(callback: CallbackQuery) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    parts = callback.data.split(":")
    try:
        page = int(parts[2])
        sort = parts[3] if len(parts) > 3 else "new"
    except (IndexError, ValueError):
        page = 0
        sort = "new"
    if sort not in {"new", "old"}:
        sort = "new"
    service = ReferralService()
    text, items, page, total_pages = await service.referred_users_page(
        callback.from_user.id,
        page,
        sort_newest_first=sort == "new",
    )
    if not items and page == 0:
        markup = inline_referral_stats_menu(lang)
    else:
        markup = inline_referral_list_menu(page, total_pages, sort=sort, lang=lang)
    await safe_edit(
        callback.message,
        text,
        markup,
        parse_mode=None,
    )
    await _track(None, "bot.referral", {"action": "list", "page": page, "sort": sort})


async def _referral_available(telegram_id: int) -> Decimal | None:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return None
        stats = await ReferralService().get_stats(session, user)
        return stats["available"]


@router.callback_query(F.data == "ref:withdraw")
async def referral_withdraw_callback(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    available = await _referral_available(callback.from_user.id)
    if available is None:
        await callback.message.answer(t("error_need_start_short", lang))
        return
    if available < MIN_WITHDRAWAL_RUB:
        await callback.message.answer(
            t(
                "withdraw_min",
                lang,
                min=format_balance(MIN_WITHDRAWAL_RUB),
                available=format_balance(available),
            )
        )
        return

    await state.set_state(BotStates.waiting_withdrawal_amount)
    await callback.message.answer(
        t(
            "withdraw_ask_amount",
            lang,
            available=format_balance(available),
            min=format_balance(MIN_WITHDRAWAL_RUB),
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t("btn_withdraw_all", lang, amount=format_balance(available)),
                        callback_data="ref:amount_all",
                    )
                ],
                [InlineKeyboardButton(text=t("btn_home", lang), callback_data="nav:back:main")],
            ]
        ),
    )


async def _ask_withdrawal_wallet(message: Message, state: FSMContext, telegram_id: int) -> None:
    lang = await _user_language(telegram_id)
    saved_wallet = await ReferralService().get_saved_wallet(telegram_id)
    if saved_wallet:
        await state.set_state(BotStates.waiting_withdrawal_wallet)
        await message.answer(
            t("withdraw_wallet_ask_saved", lang, wallet=saved_wallet),
            reply_markup=inline_withdraw_wallet_menu(saved_wallet, lang),
        )
        return
    await state.set_state(BotStates.waiting_withdrawal_wallet)
    await message.answer(t("withdraw_wallet_ask_new", lang))


async def _finish_withdrawal(
    message: Message, state: FSMContext, telegram_id: int, wallet: str
) -> None:
    data = await state.get_data()
    amount = Decimal(data.get("withdrawal_amount", "0"))
    try:
        reply = await ReferralService().create_withdrawal_for_telegram(
            telegram_id, amount=amount, wallet=wallet
        )
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.clear()
    await message.answer(reply, reply_markup=await _user_main_menu(telegram_id))
    await _track(None, "bot.referral_withdraw", {"telegram_id": telegram_id, "amount": str(amount)})


@router.callback_query(F.data == "ref:amount_all")
async def referral_amount_all_callback(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    available = await _referral_available(callback.from_user.id)
    if available is None or available < MIN_WITHDRAWAL_RUB:
        await state.clear()
        await callback.message.answer(t("withdraw_insufficient", lang))
        return
    await state.update_data(withdrawal_amount=str(available))
    await _ask_withdrawal_wallet(callback.message, state, callback.from_user.id)


@router.callback_query(F.data == "ref:wallet_saved")
async def referral_wallet_saved_callback(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    wallet = await ReferralService().get_saved_wallet(callback.from_user.id)
    if not wallet:
        await callback.message.answer(t("withdraw_wallet_missing", lang))
        return
    await _finish_withdrawal(callback.message, state, callback.from_user.id, wallet)


@router.callback_query(F.data == "ref:wallet_new")
async def referral_wallet_new_callback(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    await state.set_state(BotStates.waiting_withdrawal_wallet)
    await callback.message.answer(t("withdraw_wallet_change", lang))


@router.callback_query(F.data.startswith("bill:"))
async def billing_callback(callback: CallbackQuery) -> None:
    lang = await _user_language(callback.from_user.id)
    billing = BillingService()
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer()
        return

    _, action, value = parts[0], parts[1], parts[2]
    if action == "spend":
        await callback.answer()
        page = int(value)
        text, page, total_pages = await billing.spending_history_page(callback.from_user.id, page)
        markup = inline_spending_menu(page, max(total_pages, 1), lang)
        await safe_edit(callback.message, text, markup, parse_mode=None)
        return

    try:
        if action == "topup":
            text, pay_url = await billing.create_topup_for_telegram(
                callback.from_user.id, Decimal(value)
            )
        elif action == "sub":
            text, pay_url = await billing.create_subscription_for_telegram(
                callback.from_user.id, value
            )
        else:
            await callback.answer()
            return
    except PlategaAPIError as exc:
        logger.warning("Platega payment creation failed: %s", exc)
        await callback.answer(t("billing_payment_failed", lang), show_alert=True)
        return
    except Exception:
        logger.exception("billing callback failed")
        await callback.answer(t("error_generic", lang), show_alert=True)
        return

    await callback.answer()
    markup = inline_payment_menu(pay_url, lang) if pay_url else await _user_main_menu(callback.from_user.id)
    await present_rich_panel(callback.message, text, reply_markup=markup)


@router.callback_query(F.data == "nav:readings")
async def nav_readings_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _open_readings_menu(callback, state)


@router.callback_query(F.data.startswith("nav:reading:"))
async def nav_reading_type_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _open_reading_type(callback, state, callback.data.removeprefix("nav:reading:"))


async def _open_readings_menu(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    try:
        onboarding = OnboardingService()
        if not await onboarding.is_onboarded(callback.from_user):
            await safe_callback_answer(callback, t("error_finish_onboarding_alert", lang), show_alert=True)
            return
        await state.clear()
        await safe_callback_answer(callback)
        await present_rich_panel(
            callback.message,
            await _readings_menu_text(callback.from_user.id),
            reply_markup=inline_readings_menu(lang),
            edit_message=callback.message,
        )
        await _track(None, "bot.menu", {"item": "readings"})
    except Exception as exc:
        logger.exception("open_readings_menu failed")
        await safe_callback_answer(callback, t("error_open_readings", lang), show_alert=True)
        await _track(None, "bot.error", {"handler": "nav_readings", "error": str(exc)})


async def _open_reading_type(callback: CallbackQuery, state: FSMContext, reading_type: str) -> None:
    lang = await _user_language(callback.from_user.id)
    try:
        onboarding = OnboardingService()
        if not await onboarding.is_onboarded(callback.from_user):
            await safe_callback_answer(callback, t("error_finish_onboarding_alert", lang), show_alert=True)
            return

        tarot = TarotService()
        ok, limit_error = await tarot.ensure_can_read_today(callback.from_user.id)
        if not ok:
            await safe_callback_answer(callback, limit_error or t("error_reading_limit", lang), show_alert=True)
            return

        label = reading_label(reading_type, lang)
        await state.set_state(BotStates.waiting_reading_question)
        await state.update_data(reading_type=reading_type)
        await safe_callback_answer(callback)
        await present_rich_panel(
            callback.message,
            t("reading_ask_question", lang, label=label),
            reply_markup=inline_reading_prompt(reading_type, lang),
            edit_message=callback.message,
        )
    except Exception as exc:
        logger.exception("open_reading_type failed")
        await safe_callback_answer(callback, t("error_pick_reading", lang), show_alert=True)
        await _track(None, "bot.error", {"handler": "nav_reading_type", "error": str(exc)})


@router.callback_query(F.data.startswith("nav:"))
async def nav_callback(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await safe_callback_answer(callback)
    action = callback.data.removeprefix("nav:")
    tarot = TarotService()
    onboarding = OnboardingService()

    if not await onboarding.is_onboarded(callback.from_user):
        await callback.message.answer(t("error_finish_onboarding", lang))
        return

    if action == "main":
        await state.clear()
        menu_text, menu_markup = await _main_menu_inline(callback.from_user.id)
        await present_rich_panel(
            callback.message, menu_text, reply_markup=menu_markup, edit_message=callback.message
        )
        return

    if action == "daily":
        await _send_daily_card(callback.message, callback.from_user.id)
        menu_text, menu_markup = await _main_menu_inline(callback.from_user.id)
        await present_rich_panel(
            callback.message, menu_text, reply_markup=menu_markup, edit_message=callback.message
        )
        await _track(None, "bot.daily_card", {"telegram_id": callback.from_user.id})
        return

    if action == "history":
        await _show_reading_history(callback.message, callback.from_user.id, edit_message=callback.message)
        await _track(None, "bot.menu", {"item": "history"})
        return

    if action == "profile":
        text = await tarot.profile_extended_for_telegram(callback.from_user.id)
        await safe_edit(callback.message, text, inline_profile_menu(lang), parse_mode=None)
        await _track(None, "bot.menu", {"item": "profile"})
        return

    if action == "billing":
        text = await BillingService().panel_text(callback.from_user.id)
        await present_rich_panel(
            callback.message,
            text,
            reply_markup=inline_billing_menu(lang),
            edit_message=callback.message,
        )
        await _track(None, "bot.menu", {"item": "billing"})
        return

    if action == "referrals":
        await _open_referrals(
            callback.message,
            edit_message=callback.message,
            telegram_id=callback.from_user.id,
        )
        await _track(None, "bot.menu", {"item": "referrals"})
        return

    if action == "settings":
        lang = await SettingsService().get_ui_language(callback.from_user.id)
        text = await SettingsService().get_panel_text(callback.from_user.id)
        await present_rich_panel(
            callback.message,
            text,
            reply_markup=inline_settings_menu(lang),
            edit_message=callback.message,
        )
        await _track(None, "bot.menu", {"item": "settings"})
        return

    if action == "language":
        lang = await SettingsService().get_ui_language(callback.from_user.id)
        await present_rich_panel(
            callback.message,
            t("choose_language", lang),
            reply_markup=inline_language_menu(lang),
            edit_message=callback.message,
        )
        await _track(None, "bot.menu", {"item": "language"})
        return

    if action == "info":
        await present_rich_panel(
            callback.message,
            info_panel_text(lang),
            reply_markup=inline_info_menu(lang),
            edit_message=callback.message,
        )
        await _track(None, "bot.menu", {"item": "info"})
        return

    if action == "profile_edit":
        await _show_profile_edit(callback.message, callback.from_user.id)
        await _track(None, "bot.menu", {"item": "profile_edit"})
        return


@router.callback_query(F.data == "onb:back")
async def onboarding_back(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    await state.clear()
    service = OnboardingService()
    prompt, user_id = await service.go_back(callback.from_user)
    if not prompt:
        return

    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == callback.from_user.id))
        if user is None:
            return
        from app.database.models import OnboardingSession

        onboarding = await session.scalar(
            select(OnboardingSession).where(
                OnboardingSession.user_id == user.id,
                OnboardingSession.completed_at.is_(None),
            )
        )
        step_key = onboarding.current_step if onboarding else ONBOARDING_STEPS[0][0]

    await safe_edit(callback.message, prompt, onboarding_keyboard(step_key, lang))
    await _track(user_id, "bot.onboarding_back", {"step": step_key})


@router.callback_query(F.data.startswith("onb:pick:"))
async def onboarding_pick(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await callback.answer()
    parts = callback.data.split(":", 3)
    if len(parts) < 4:
        return

    _, _, _step_key, value = parts
    await _process_onboarding_answer(callback, value, edit=True)


@router.callback_query(F.data.startswith("photo:mode:"))
async def photo_mode_callback(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _user_language(callback.from_user.id)
    await safe_callback_answer(callback)
    onboarding = OnboardingService()
    if not await onboarding.is_onboarded(callback.from_user):
        await callback.message.answer(t("error_finish_onboarding", lang))
        return

    data = await state.get_data()
    file_id = data.get("photo_file_id")
    if not file_id:
        await callback.message.answer(t("error_photo_not_found", lang))
        await state.clear()
        return

    mode = callback.data.removeprefix("photo:mode:")
    if mode == "other":
        await state.set_state(BotStates.waiting_photo_custom_request)
        await state.update_data(photo_file_id=file_id)
        await callback.message.answer(t("error_photo_ask", lang))
        return

    if mode not in {"aura", "palm"}:
        await callback.message.answer(t("error_unknown_photo_mode", lang))
        return

    _fire_and_forget(
        _process_photo_request_safe(
            callback.message,
            state,
            file_id=file_id,
            mode=mode,
            telegram_user=callback.from_user,
        )
    )


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer()


async def _process_onboarding_answer(
    source: Message | CallbackQuery,
    answer: str,
    *,
    edit: bool,
) -> None:
    telegram_user = source.from_user
    lang = await _user_language(telegram_user.id)
    service = OnboardingService()
    onboarding_reply, user_id, completed = await service.handle_answer(telegram_user, answer)
    if not onboarding_reply:
        return

    next_step_key = None
    if not completed:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user:
                from app.database.models import OnboardingSession

                onboarding = await session.scalar(
                    select(OnboardingSession).where(
                        OnboardingSession.user_id == user.id,
                        OnboardingSession.completed_at.is_(None),
                    )
                )
                next_step_key = onboarding.current_step if onboarding else None

    markup = onboarding_keyboard(next_step_key, lang) if next_step_key else None
    reply_text = onboarding_reply
    if markup is None and not completed:
        reply_text = f"{onboarding_reply}\n\n{t('onboarding_type_hint', lang)}"

    if isinstance(source, CallbackQuery):
        if completed:
            await source.message.answer(
                onboarding_reply,
                reply_markup=await _user_main_menu(telegram_user.id),
            )
            await source.message.answer(t("first_daily_gift", await _user_language(telegram_user.id)))
            await _send_daily_card(source.message, telegram_user.id)
            menu_text, menu_markup = await _main_menu_inline(telegram_user.id)
            await present_rich_panel(source.message, menu_text, reply_markup=menu_markup)
        elif edit:
            await safe_edit(source.message, reply_text, markup)
        else:
            await source.message.answer(reply_text, reply_markup=markup)
    else:
        if completed:
            await source.answer(onboarding_reply, reply_markup=await _user_main_menu(telegram_user.id))
            await source.answer(t("first_daily_gift", await _user_language(telegram_user.id)))
            await _send_daily_card(source, telegram_user.id)
            menu_text, menu_markup = await _main_menu_inline(telegram_user.id)
            await present_rich_panel(source, menu_text, reply_markup=menu_markup)
        else:
            await source.answer(reply_text, reply_markup=markup)

    event = "bot.onboarding_complete" if completed else "bot.onboarding_step"
    await _track(user_id, event, {"text": answer[:200]})


# Single supported voice for spoken replies (selection removed from settings).
DEFAULT_VOICE_PRESET = "female_mystical"


async def _user_voice_settings(telegram_id: int) -> tuple[str, str]:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return "free", DEFAULT_VOICE_PRESET
        subscription = await session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        tier = subscription.tier if subscription else "free"
        return tier, DEFAULT_VOICE_PRESET


@router.message(F.voice)
async def voice_message(message: Message) -> None:
    lang = await _user_language(message.from_user.id)
    if message.voice is None or message.from_user is None:
        return

    onboarding = OnboardingService()
    if not await onboarding.is_onboarded(message.from_user):
        await message.answer(t("error_finish_onboarding", lang))
        return

    tier, voice_preset = await _user_voice_settings(message.from_user.id)
    voice_reply = can_use_premium_voice(tier)

    status_msg = None
    try:
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        status_msg = await send_processing_placeholder(message, kind="voice")
        audio_file = await store_telegram_voice(message.bot, message.voice.file_id)
        voice_service = VoiceService()
        db_user_id = await _get_user_id(message.from_user.id)
        transcript = await voice_service.transcribe(audio_file, user_id=db_user_id)

        orchestrator = AIOrchestrator()
        user_id, messages, error, user_message_id, billing_mode = await orchestrator.prepare_chat(
            message.from_user, transcript
        )
        if error:
            await message.answer(error)
            return

        if billing_mode == "balance":
            await message.answer(t("error_free_messages_ended", lang))

        answer = await _generate_with_typing(
            message,
            orchestrator.generate_chat(messages or []),
        )

        usage = await orchestrator.complete_chat(
            user_id or "",
            transcript,
            answer,
            user_message_id=user_message_id,
            context_messages=messages,
            billing_mode=billing_mode,
        )
        menu = await _user_main_menu(message.from_user.id)

        if voice_reply:
            stop_record = asyncio.Event()
            record_task = asyncio.create_task(
                chat_action_loop(message.bot, message.chat.id, ChatAction.RECORD_VOICE, stop_record)
            )
            try:
                audio_reply_url = await voice_service.synthesize_audio_url(
                    user_id or "",
                    answer,
                    preset=voice_preset,
                )
            finally:
                stop_record.set()
                await record_task

            if await send_voice_from_url(message, audio_reply_url):
                await clear_processing_placeholder(status_msg)
                status_msg = None
                await _notify_billing(
                    message,
                    billing_mode,
                    usage,
                    reply_markup=menu,
                )
            else:
                await _answer_formatted(message, answer)
                await clear_processing_placeholder(status_msg)
                status_msg = None
                await _notify_billing(
                    message,
                    billing_mode,
                    usage,
                    reply_markup=menu,
                )
                await message.answer(t("error_voice_send", lang))
        else:
            await _answer_formatted(message, answer)
            await clear_processing_placeholder(status_msg)
            status_msg = None
            await _notify_billing(
                message,
                billing_mode,
                usage,
                reply_markup=menu,
            )

        await _track(user_id, "bot.voice", {"telegram_id": message.from_user.id})
    except Exception as exc:
        logger.exception("Voice message failed: %s", exc)
        await _track(
            None,
            "bot.error",
            {"handler": "voice", "error": str(exc), "traceback": traceback.format_exc()[-2000:]},
        )
        detail = str(exc).strip()
        if detail and len(detail) < 120:
            await message.answer(t("error_voice_process", lang, detail=detail))
        else:
            await message.answer(t("error_voice_process_generic", lang))
    finally:
        await clear_processing_placeholder(status_msg)


@router.message(F.photo)
async def photo_message(message: Message, state: FSMContext) -> None:
    lang = await _user_language(message.from_user.id)
    try:
        onboarding = OnboardingService()
        if not await onboarding.is_onboarded(message.from_user):
            await message.answer(t("error_finish_onboarding", lang))
            return

        file_id = message.photo[-1].file_id
        caption = (message.caption or "").strip()

        if caption:
            _fire_and_forget(
                _process_photo_request_safe(
                    message,
                    state,
                    file_id=file_id,
                    mode="custom",
                    custom_text=caption,
                )
            )
            return

        await state.set_state(BotStates.waiting_photo_mode)
        await state.update_data(photo_file_id=file_id)
        await message.answer(
            t("photo_received_prompt", lang),
            reply_markup=inline_photo_mode_menu(lang),
        )
    except Exception as exc:
        await _track(None, "bot.error", {"handler": "photo_message", "error": str(exc)})
        await message.answer(t("error_photo_accept", lang))


@router.message()
async def fallback_message(message: Message, state: FSMContext) -> None:
    lang = await _user_language(message.from_user.id)
    try:
        text = (message.text or "").strip()
        onboarding = OnboardingService()

        current_state = await state.get_state()

        if not await onboarding.is_onboarded(message.from_user):
            if text in all_menu_texts():
                await message.answer(t("error_finish_onboarding_step", lang))
                return
            if text:
                await _process_onboarding_answer(message, text, edit=False)
            return

        # Menu buttons cancel any stale feature FSM and open the chosen section.
        if is_home_button(text):
            await _go_home(message, state)
            return

        if is_balance_button(text):
            await state.clear()
            await _open_billing(message)
            return

        if text in all_menu_texts():
            await _handle_menu_text(message, state, text)
            return

        if current_state in _FEATURE_WAIT_STATES:
            normalized = text.lower()
            if not text or normalized in _CHAT_ESCAPE_WORDS:
                await state.clear()
                return

        if current_state == BotStates.waiting_profile_field.state:
            data = await state.get_data()
            field_key = data.get("profile_field")
            await state.clear()
            if not field_key:
                await message.answer(t("error_field_unknown", lang))
                return
            service = ProfileService()
            result = await service.update_field(message.from_user.id, field_key, text)
            if result is None:
                await message.answer(t("error_update_field", lang))
                return
            await message.answer(result)
            await _show_profile_edit(message, message.from_user.id)
            await _track(None, "bot.profile_edit", {"field": field_key})
            return

        if current_state == BotStates.waiting_memory_add.state:
            data = await state.get_data()
            page = int(data.get("memory_return_page", 0))
            await state.clear()
            ok, result_text = await MemoryPanelService().add_manual(message.from_user.id, text)
            await message.answer(result_text)
            if ok:
                await _show_memory_list(message, message.from_user.id, page)
                await _track(None, "bot.memory", {"action": "add"})
            return

        if current_state == BotStates.waiting_photo_mode.state:
            await message.answer(t("choose_photo_mode", lang))
            return

        if current_state == BotStates.waiting_withdrawal_amount.state:
            amount = parse_withdrawal_amount(text or "")
            if amount is None:
                await message.answer(t("withdraw_amount_invalid", lang))
                return
            if amount < MIN_WITHDRAWAL_RUB:
                await message.answer(
                    t("withdraw_amount_min", lang, min=format_balance(MIN_WITHDRAWAL_RUB))
                )
                return
            available = await _referral_available(message.from_user.id)
            if available is None or amount > available:
                await message.answer(
                    t(
                        "withdraw_amount_over",
                        lang,
                        available=format_balance(available or Decimal("0")),
                    )
                )
                return
            await state.update_data(withdrawal_amount=str(amount))
            await _ask_withdrawal_wallet(message, state, message.from_user.id)
            return

        if current_state == BotStates.waiting_withdrawal_wallet.state:
            wallet = (text or "").strip()
            if not is_valid_trc20_wallet(wallet):
                await message.answer(t("withdraw_wallet_invalid", lang))
                return
            await _finish_withdrawal(message, state, message.from_user.id, wallet)
            return

        if current_state == BotStates.waiting_photo_custom_request.state:
            data = await state.get_data()
            file_id = data.get("photo_file_id")
            if not file_id:
                await state.clear()
                await message.answer(t("error_photo_not_found", lang))
                return
            if not text:
                await message.answer(t("error_photo_ask", lang))
                return
            _fire_and_forget(
                _process_photo_request_safe(
                    message,
                    state,
                    file_id=file_id,
                    mode="custom",
                    custom_text=text,
                )
            )
            return

        # Feature prompts — only after explicit inline-menu selection (FSM set there).
        if current_state == BotStates.waiting_reading_question.state:
            if not text:
                await message.answer(t("reading_ask_question_text", lang))
                return
            await _handle_reading_question(message, state, text)
            return

        if current_state == BotStates.waiting_zen_question.state:
            await handle_zen_question(message, text, state)
            return

        if current_state == BotStates.waiting_rune_question.state:
            await handle_rune_question(message, text, state)
            return

        if current_state == BotStates.waiting_stone_query.state:
            await handle_stone_query(message, text, state)
            return

        if current_state == BotStates.waiting_bracelet_query.state:
            await handle_bracelet_query(message, text, state)
            return

        if not text:
            return

        await _chat_reply(message, text, state=state)
    except Exception as exc:
        logger.exception("fallback_message failed")
        await _track(
            None,
            "bot.error",
            {"handler": "message", "error": str(exc), "traceback": traceback.format_exc()[-2000:]},
        )
        await message.answer(t("error_process_message", lang))


async def _handle_menu_text(message: Message, state: FSMContext, text: str) -> None:
    tarot = TarotService()
    await state.clear()
    lang = await _user_language(message.from_user.id)
    action = menu_actions(lang).get(text) or MENU_ACTIONS.get(text)

    if action == "home":
        await _go_home(message, state)
        await _track(None, "bot.menu", {"item": "home"})
        return

    if action == "zen":
        from app.bot.keyboards import inline_zen_menu

        await present_rich_panel(message, t("zen_menu_text", lang), reply_markup=inline_zen_menu(lang))
        await _track(None, "bot.menu", {"item": "zen"})
        return

    if action == "energy":
        from app.bot.keyboards import inline_energy_menu

        await present_rich_panel(message, t("energy_menu_text", lang), reply_markup=inline_energy_menu(lang))
        await _track(None, "bot.menu", {"item": "energy"})
        return

    if action == "daily":
        await _send_daily_card(message, message.from_user.id)
        await _track(None, "bot.daily_card", {"telegram_id": message.from_user.id})
        return

    if action == "readings":
        await present_rich_panel(
            message,
            await _readings_menu_text(message.from_user.id),
            reply_markup=inline_readings_menu(lang),
        )
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "history":
        await _show_reading_history(message, message.from_user.id)
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "profile":
        await message.answer(
            await tarot.profile_extended_for_telegram(message.from_user.id),
            reply_markup=inline_profile_menu(lang),
            parse_mode=None,
        )
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "billing":
        await _open_billing(message)
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "settings":
        await present_rich_panel(
            message,
            await SettingsService().get_panel_text(message.from_user.id),
            reply_markup=inline_settings_menu(lang),
        )
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "language":
        await present_rich_panel(message, t("choose_language", lang), reply_markup=inline_language_menu(lang))
        await _track(None, "bot.menu", {"item": "language"})
        return

    if action == "info":
        await present_rich_panel(message, info_panel_text(lang), reply_markup=inline_info_menu(lang))
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "support":
        await present_rich_panel(
            message,
            t("support_message", lang),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=t("btn_open_support", lang), url=support_url())]
                ]
            ),
        )
        await _track(None, "bot.menu", {"item": text})
        return

    menu_text, menu_markup = await _main_menu_inline(message.from_user.id)
    await present_rich_panel(message, menu_text, reply_markup=menu_markup)


@router.message(F.sticker)
async def sticker_file_id_hint(message: Message) -> None:
    if message.from_user is None or message.sticker is None:
        return

    sticker = message.sticker
    logger.info(
        "Sticker from user %s file_id=%s unique_id=%s",
        message.from_user.id,
        sticker.file_id,
        sticker.file_unique_id,
    )
    if message.from_user.id not in _admin_telegram_ids():
        return

    await message.answer(
        "Скопируй в TELEGRAM_PLACEHOLDER_STICKER_ID:\n\n"
        f"<code>{sticker.file_id}</code>",
        parse_mode=ParseMode.HTML,
    )


def register_handlers(dispatcher: Dispatcher) -> None:
    dispatcher.include_router(feature_router)
    dispatcher.include_router(router)
