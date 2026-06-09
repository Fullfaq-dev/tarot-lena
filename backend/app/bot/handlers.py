import asyncio
from decimal import Decimal

from aiogram import Dispatcher, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.bot.cards_media import send_drawn_cards
from app.core.config import get_settings
from app.bot.helpers import safe_edit
from app.bot.keyboards import (
    MAIN_MENU_TEXT,
    MENU_TEXTS,
    ONBOARDING_CHOICES,
    READING_LABEL_TO_TYPE,
    READING_TYPE_LABELS,
    READINGS_MENU_TEXT,
    inline_billing_menu,
    inline_history_menu,
    inline_main_menu,
    inline_photo_mode_menu,
    inline_profile_edit_menu,
    inline_reading_prompt,
    inline_readings_menu,
    inline_settings_menu,
    is_balance_button,
    main_menu,
    onboarding_keyboard,
    profile_field_keyboard,
)
from app.bot.states import BotStates
from app.bot.streaming import stream_to_message
from app.database.models import Subscription, User
from app.database.session import AsyncSessionLocal
from app.services.ai.orchestrator import AIOrchestrator
from app.services.analytics.tracker import track_event
from app.services.billing.limits import FREE_CHAT_MESSAGES_PER_MONTH, free_messages_left
from app.services.billing.tokens import format_balance
from app.services.billing.service import BillingService
from app.services.onboarding.service import ONBOARDING_STEPS, OnboardingService
from app.services.profile.service import ProfileService
from app.services.settings.service import SettingsService
from app.services.tarot.service import READING_TYPES, TarotService
from app.services.vision.service import VisionService

router = Router()


async def _track(user_id: str | None, event: str, payload: dict | None = None) -> None:
    asyncio.create_task(track_event(event, user_id=user_id, payload=payload))


async def _get_user_id(telegram_id: int) -> str | None:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        return user.id if user else None


async def _user_main_menu(telegram_id: int):
    balance = await BillingService().get_balance_label(telegram_id)
    return main_menu(balance)


async def _refresh_main_menu(message: Message) -> None:
    try:
        await message.answer("\u2063", reply_markup=await _user_main_menu(message.from_user.id))
    except Exception:
        pass


async def _open_billing(message: Message, *, edit_message: Message | None = None) -> None:
    text = await BillingService().panel_text(message.from_user.id)
    markup = inline_billing_menu()
    if edit_message is not None:
        await safe_edit(edit_message, text, markup)
    else:
        await message.answer(text, reply_markup=markup, parse_mode=None)


async def _with_typing(message: Message, coro):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    return await coro


async def _handle_reading_question(message: Message, state: FSMContext, question: str) -> None:
    data = await state.get_data()
    reading_type = data.get("reading_type", "past_present_future")
    await state.clear()

    user_id = await _get_user_id(message.from_user.id)
    if user_id is None:
        await message.answer("Сначала нажми /start, чтобы я создала твой профиль.")
        return

    tarot = TarotService()
    orchestrator = AIOrchestrator()
    label = READING_TYPE_LABELS.get(reading_type, reading_type)
    cards = tarot.draw_cards(READING_TYPES.get(reading_type, 3))
    await send_drawn_cards(message, cards)
    card_lines = "\n".join(f"• {card['name']}" for card in cards)
    prefix = f"Расклад: {label}\nВопрос: {question}\n\nКарты:\n{card_lines}\n\n"

    user_db_id, messages, error, user_message_id, billing_mode = await orchestrator.prepare_tarot_reading(
        message.from_user, question, cards, reading_type
    )
    if error:
        await message.answer(error)
        return

    if billing_mode == "balance":
        await message.answer("Бесплатные сообщения закончились. Ответ спишется с баланса.")

    interpretation = await stream_to_message(
        message,
        orchestrator.stream_chat(messages or []),
        prefix=prefix,
    )
    if not interpretation or "cannot fulfill" in interpretation.lower():
        interpretation = tarot.interpret_locally(question, cards)

    usage = await orchestrator.complete_chat(
        user_db_id or user_id,
        question,
        interpretation,
        user_message_id=user_message_id,
        context_messages=messages,
        feature="tarot_reading",
        billing_mode=billing_mode,
    )
    await _notify_billing(message, billing_mode, usage)
    await tarot.create_reading(
        user_id,
        reading_type,
        question,
        cards=cards,
        interpretation=interpretation,
    )
    await _refresh_main_menu(message)
    await _track(user_id, "bot.reading", {"reading_type": reading_type})


async def _notify_billing(message: Message, billing_mode: str, usage: dict) -> None:
    charged = Decimal(str(usage.get("charged_rub", "0")))
    image_charged = Decimal(str(usage.get("image_charged_rub", "0")))
    if charged > 0:
        parts = [f"Списано {charged} ₽"]
        if image_charged > 0:
            parts.append(f"включая инфографику {image_charged} ₽")
        parts.append(f"Остаток на балансе: {format_balance(usage.get('balance_after'))}.")
        await message.answer(" ".join(parts))
        return
    if billing_mode == "free" and free_messages_left(
        (await _get_user_free_used(message.from_user.id))
    ) == 0:
        await message.answer(
            f"Это было последнее бесплатное сообщение в этом месяце ({FREE_CHAT_MESSAGES_PER_MONTH}). "
            "Дальше ответы списываются с баланса — пополни его в разделе «Баланс»."
        )


async def _process_photo_request(
    message: Message,
    state: FSMContext,
    *,
    file_id: str,
    mode: str,
    custom_text: str = "",
) -> None:
    await state.clear()
    user_id = await _get_user_id(message.from_user.id)
    if user_id is None:
        await message.answer("Сначала нажми /start, чтобы я создала твой профиль.")
        return

    settings = get_settings()
    waiting_msg = await message.answer("Смотрю на фото и готовлю ответ…")
    if settings.telegram_placeholder_sticker_id:
        try:
            await message.answer_sticker(settings.telegram_placeholder_sticker_id)
        except Exception:
            pass

    if mode in {"aura", "palm"}:
        await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)

    result, error = await VisionService().process_photo(
        message.bot,
        message.from_user,
        file_id=file_id,
        mode=mode,
        custom_text=custom_text,
    )

    try:
        await waiting_msg.delete()
    except Exception:
        pass

    if error:
        await message.answer(error)
        return

    await message.answer(result.interpretation, parse_mode=None)

    if result.infographic_urls:
        caption = "Инфографика готова ✨"
        sent = False
        for url in result.infographic_urls:
            try:
                await message.answer_photo(url, caption=caption)
                sent = True
                break
            except Exception:
                continue
        if not sent:
            await message.answer("Инфографика сгенерирована, но не удалось отправить изображение. Попробуй ещё раз.")

    await _notify_billing(message, result.billing_mode, result.usage)
    await _refresh_main_menu(message)
    await _track(user_id, "bot.vision", {"mode": mode, "feature": result.feature})


async def _get_user_free_used(telegram_id: int) -> int:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        return user.free_messages_used_month if user else 0


async def _stream_chat_reply(message: Message, text: str) -> None:
    orchestrator = AIOrchestrator()
    user_id, messages, error, user_message_id, billing_mode = await orchestrator.prepare_chat(
        message.from_user, text
    )
    if error:
        await message.answer(error)
        return

    if billing_mode == "balance":
        await message.answer("Бесплатные сообщения закончились. Ответ спишется с баланса.")

    answer = await stream_to_message(message, orchestrator.stream_chat(messages or []))
    usage = await orchestrator.complete_chat(
        user_id or "",
        text,
        answer,
        user_message_id=user_message_id,
        context_messages=messages,
        billing_mode=billing_mode,
    )
    await _notify_billing(message, billing_mode, usage)
    await _refresh_main_menu(message)
    await _track(user_id, "bot.chat", {"telegram_id": message.from_user.id, "length": len(text)})


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        service = OnboardingService()
        text, user_id, is_new = await service.start_or_resume(telegram_user=message.from_user)
        onboarded = await service.is_onboarded(message.from_user)

        if onboarded:
            await message.answer(text, reply_markup=await _user_main_menu(message.from_user.id))
            await message.answer(MAIN_MENU_TEXT, reply_markup=inline_main_menu())
        else:
            step_key = await service.get_current_step_key(message.from_user) or ONBOARDING_STEPS[0][0]
            markup = onboarding_keyboard(step_key)
            hint = ""
            if markup is None:
                hint = "\n\nНапиши ответ обычным сообщением в чат."
            await message.answer(f"{text}{hint}", reply_markup=markup)

        await _track(
            user_id,
            "bot.user_created" if is_new else "bot.command_start",
            {"telegram_id": message.from_user.id if message.from_user else None},
        )
    except Exception as exc:
        await _track(None, "bot.error", {"handler": "start", "error": str(exc)})
        await message.answer("Что-то пошло не так. Попробуй ещё раз через минуту.")


@router.callback_query(F.data == "nav:noop")
async def nav_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("nav:back:"))
async def nav_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    target = callback.data.removeprefix("nav:back:")
    await state.clear()

    if target == "main":
        await safe_edit(callback.message, MAIN_MENU_TEXT, inline_main_menu())
        return

    if target == "readings":
        await safe_edit(callback.message, READINGS_MENU_TEXT, inline_readings_menu())
        return


@router.callback_query(F.data.startswith("hist:open:"))
async def history_open(callback: CallbackQuery) -> None:
    await callback.answer()
    reading_id = callback.data.removeprefix("hist:open:")
    tarot = TarotService()
    detail = await tarot.reading_detail_for_telegram(callback.from_user.id, reading_id)
    if detail is None:
        await callback.message.answer("Расклад не найден.")
        return
    await callback.message.answer(detail, parse_mode=None)


async def _show_profile_edit(target: Message, telegram_id: int, *, prefix: str = "") -> None:
    service = ProfileService()
    error, rows = await service.get_profile_summary(telegram_id)
    if error:
        await target.answer(error)
        return
    text = (
        f"{prefix}Данные анкеты\n\n"
        "Нажми поле, которое хочешь изменить. Новое значение сразу попадёт в профиль и в контекст ИИ."
    )
    await safe_edit(target, text, inline_profile_edit_menu(rows))


@router.callback_query(F.data.startswith("set:prof:"))
async def profile_field_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    field_key = callback.data.removeprefix("set:prof:")
    service = ProfileService()
    prompt = service.prompt_for_field(field_key)

    if field_key in ONBOARDING_CHOICES:
        await safe_edit(
            callback.message,
            f"Выбери новое значение.\n{prompt}",
            profile_field_keyboard(field_key),
        )
        return

    await state.set_state(BotStates.waiting_profile_field)
    await state.update_data(profile_field=field_key)
    await safe_edit(
        callback.message,
        f"{prompt}\n\nНапиши новое значение обычным сообщением в чат.",
        profile_field_keyboard(field_key),
    )


@router.callback_query(F.data.startswith("prof:pick:"))
async def profile_field_pick(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    payload = callback.data.removeprefix("prof:pick:")
    field_key, _, value = payload.partition(":")
    if not field_key or not value:
        return

    if value == "другое" and field_key == "main_concern":
        await state.set_state(BotStates.waiting_profile_field)
        await state.update_data(profile_field=field_key)
        await safe_edit(
            callback.message,
            "Напиши своими словами, что сейчас беспокоит больше всего.",
            profile_field_keyboard(field_key),
        )
        return

    service = ProfileService()
    result = await service.update_field(callback.from_user.id, field_key, value)
    if result is None:
        await callback.message.answer("Не удалось обновить поле.")
        return
    await _show_profile_edit(callback.message, callback.from_user.id, prefix=f"{result}\n\n")
    await _track(None, "bot.profile_edit", {"field": field_key})


@router.callback_query(F.data.startswith("set:"))
async def settings_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    service = SettingsService()
    action = callback.data.removeprefix("set:")

    if action == "voice":
        text = await service.cycle_voice(callback.from_user.id)
    elif action == "timezone":
        text = await service.cycle_timezone(callback.from_user.id)
    elif action == "toggle:daily":
        text = await service.toggle_daily_card(callback.from_user.id)
    elif action == "toggle:proactive":
        text = await service.toggle_proactive(callback.from_user.id)
    else:
        text = await service.get_panel_text(callback.from_user.id)

    await safe_edit(callback.message, text, inline_settings_menu())
    await _track(None, "bot.settings", {"action": action})


@router.callback_query(F.data.startswith("bill:"))
async def billing_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    billing = BillingService()
    parts = callback.data.split(":")
    if len(parts) < 3:
        return

    _, action, value = parts[0], parts[1], parts[2]
    if action == "topup":
        text = await billing.create_topup_for_telegram(callback.from_user.id, Decimal(value))
        await callback.message.answer(text)
        await _refresh_main_menu(callback.message)
        return

    if action == "sub":
        text = await billing.create_subscription_for_telegram(callback.from_user.id, value)
        await callback.message.answer(text)
        await _refresh_main_menu(callback.message)
        return


@router.callback_query(F.data.startswith("nav:"))
async def nav_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    action = callback.data.removeprefix("nav:")
    tarot = TarotService()
    onboarding = OnboardingService()

    if not await onboarding.is_onboarded(callback.from_user):
        await callback.message.answer("Сначала давай закончим анкету — ответь на последний вопрос или нажми /start.")
        return

    if action == "main":
        await state.clear()
        await safe_edit(callback.message, MAIN_MENU_TEXT, inline_main_menu())
        return

    if action == "readings":
        await state.clear()
        await safe_edit(callback.message, READINGS_MENU_TEXT, inline_readings_menu())
        return

    if action.startswith("reading:"):
        reading_type = action.removeprefix("reading:")
        label = READING_TYPE_LABELS.get(reading_type, "расклад")
        await state.set_state(BotStates.waiting_reading_question)
        await state.update_data(reading_type=reading_type)
        await safe_edit(
            callback.message,
            f"Расклад: {label}\n\nНапиши свой вопрос обычным сообщением в чат — я сделаю расклад и объясню карты.",
            inline_reading_prompt(reading_type),
        )
        return

    if action == "daily":
        await callback.message.bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
        prediction, card = await tarot.daily_card_for_telegram(callback.from_user.id)
        if card:
            await send_drawn_cards(callback.message, [card])
        await callback.message.answer(prediction, parse_mode=None)
        await safe_edit(callback.message, MAIN_MENU_TEXT, inline_main_menu())
        await _track(None, "bot.daily_card", {"telegram_id": callback.from_user.id})
        return

    if action == "history":
        text, readings = await tarot.history_entries(callback.from_user.id)
        if readings:
            await callback.message.answer(text, reply_markup=inline_history_menu(readings), parse_mode=None)
        else:
            await callback.message.answer(text, parse_mode=None)
        await safe_edit(callback.message, MAIN_MENU_TEXT, inline_main_menu())
        await _track(None, "bot.menu", {"item": "history"})
        return

    if action == "profile":
        text = await tarot.profile_extended_for_telegram(callback.from_user.id)
        await callback.message.answer(text, parse_mode=None)
        await safe_edit(callback.message, MAIN_MENU_TEXT, inline_main_menu())
        await _track(None, "bot.menu", {"item": "profile"})
        return

    if action == "billing":
        text = await BillingService().panel_text(callback.from_user.id)
        await safe_edit(callback.message, text, inline_billing_menu())
        await _track(None, "bot.menu", {"item": "billing"})
        return

    if action == "settings":
        text = await SettingsService().get_panel_text(callback.from_user.id)
        await safe_edit(callback.message, text, inline_settings_menu())
        await _track(None, "bot.menu", {"item": "settings"})
        return

    if action == "profile_edit":
        await _show_profile_edit(callback.message, callback.from_user.id)
        await _track(None, "bot.menu", {"item": "profile_edit"})
        return


@router.callback_query(F.data == "onb:back")
async def onboarding_back(callback: CallbackQuery, state: FSMContext) -> None:
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

    await safe_edit(callback.message, prompt, onboarding_keyboard(step_key))
    await _track(user_id, "bot.onboarding_back", {"step": step_key})


@router.callback_query(F.data.startswith("onb:pick:"))
async def onboarding_pick(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    parts = callback.data.split(":", 3)
    if len(parts) < 4:
        return

    _, _, step_key, value = parts
    if value == "другое" and step_key == "main_concern":
        await state.set_state(BotStates.waiting_custom_concern)
        await safe_edit(
            callback.message,
            "Напиши своими словами, что сейчас беспокоит больше всего.",
            InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="← Назад", callback_data="onb:back")]]
            ),
        )
        return

    await _process_onboarding_answer(callback, value, edit=True)


@router.callback_query(F.data.startswith("photo:mode:"))
async def photo_mode_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    onboarding = OnboardingService()
    if not await onboarding.is_onboarded(callback.from_user):
        await callback.message.answer("Сначала давай закончим анкету — ответь на последний вопрос или нажми /start.")
        return

    data = await state.get_data()
    file_id = data.get("photo_file_id")
    if not file_id:
        await callback.message.answer("Фото не найдено. Пришли его ещё раз.")
        await state.clear()
        return

    mode = callback.data.removeprefix("photo:mode:")
    if mode == "other":
        await state.set_state(BotStates.waiting_photo_custom_request)
        await state.update_data(photo_file_id=file_id)
        await callback.message.answer("Напиши, что хочешь узнать по этому фото.")
        return

    if mode not in {"aura", "palm"}:
        await callback.message.answer("Неизвестный режим анализа.")
        return

    await _process_photo_request(
        callback.message,
        state,
        file_id=file_id,
        mode=mode,
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

    markup = onboarding_keyboard(next_step_key) if next_step_key else None
    reply_text = onboarding_reply
    if markup is None and not completed:
        reply_text = f"{onboarding_reply}\n\nНапиши ответ обычным сообщением в чат."

    if isinstance(source, CallbackQuery):
        if completed:
            await source.message.answer(
                onboarding_reply,
                reply_markup=await _user_main_menu(telegram_user.id),
            )
            await source.message.answer(MAIN_MENU_TEXT, reply_markup=inline_main_menu())
        elif edit:
            await safe_edit(source.message, reply_text, markup)
        else:
            await source.message.answer(reply_text, reply_markup=markup)
    else:
        if completed:
            await source.answer(onboarding_reply, reply_markup=await _user_main_menu(telegram_user.id))
            await source.answer(MAIN_MENU_TEXT, reply_markup=inline_main_menu())
        else:
            await source.answer(reply_text, reply_markup=markup)

    event = "bot.onboarding_complete" if completed else "bot.onboarding_step"
    await _track(user_id, event, {"text": answer[:200]})


@router.message(F.voice)
async def voice_message(message: Message) -> None:
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    await message.answer(
        "Я услышала голосовое. В полной версии я расшифрую его, отвечу текстом и при Premium отправлю голосовой ответ."
    )


@router.message(F.photo)
async def photo_message(message: Message, state: FSMContext) -> None:
    onboarding = OnboardingService()
    if not await onboarding.is_onboarded(message.from_user):
        await message.answer("Сначала давай закончим анкету — ответь на последний вопрос или нажми /start.")
        return

    file_id = message.photo[-1].file_id
    caption = (message.caption or "").strip()

    if caption:
        await _process_photo_request(
            message,
            state,
            file_id=file_id,
            mode="custom",
            custom_text=caption,
        )
        return

    await state.set_state(BotStates.waiting_photo_mode)
    await state.update_data(photo_file_id=file_id)
    await message.answer(
        "Фото получила. Что хочешь узнать по этому снимку?",
        reply_markup=inline_photo_mode_menu(),
    )


@router.message()
async def fallback_message(message: Message, state: FSMContext) -> None:
    try:
        text = (message.text or "").strip()
        onboarding = OnboardingService()

        current_state = await state.get_state()
        if current_state == BotStates.waiting_custom_concern.state:
            await state.clear()
            await _process_onboarding_answer(message, text, edit=False)
            return

        if current_state == BotStates.waiting_profile_field.state:
            data = await state.get_data()
            field_key = data.get("profile_field")
            await state.clear()
            if not field_key:
                await message.answer("Не удалось определить поле. Открой настройки и попробуй снова.")
                return
            service = ProfileService()
            result = await service.update_field(message.from_user.id, field_key, text)
            if result is None:
                await message.answer("Не удалось обновить поле.")
                return
            await message.answer(result)
            await _show_profile_edit(message, message.from_user.id)
            await _track(None, "bot.profile_edit", {"field": field_key})
            return

        if current_state == BotStates.waiting_reading_question.state:
            if not text:
                await message.answer("Напиши вопрос для расклада обычным сообщением.")
                return
            await _handle_reading_question(message, state, text)
            return

        if current_state == BotStates.waiting_photo_mode.state:
            await message.answer("Выбери вариант анализа кнопками под последним фото.")
            return

        if current_state == BotStates.waiting_photo_custom_request.state:
            data = await state.get_data()
            file_id = data.get("photo_file_id")
            if not file_id:
                await state.clear()
                await message.answer("Фото не найдено. Пришли его ещё раз.")
                return
            if not text:
                await message.answer("Напиши, что хочешь узнать по фото.")
                return
            await _process_photo_request(
                message,
                state,
                file_id=file_id,
                mode="custom",
                custom_text=text,
            )
            return

        if not await onboarding.is_onboarded(message.from_user):
            if text in MENU_TEXTS:
                await message.answer("Сначала давай закончим анкету. Ответь на вопрос выше или нажми кнопку, если она есть.")
                return

            if text:
                await _process_onboarding_answer(message, text, edit=False)
            return

        if is_balance_button(text):
            await _open_billing(message)
            return

        if text in MENU_TEXTS:
            await _handle_menu_text(message, state, text)
            return

        reading_type = READING_LABEL_TO_TYPE.get(text.lower())
        if reading_type:
            label = READING_TYPE_LABELS[reading_type]
            await state.set_state(BotStates.waiting_reading_question)
            await state.update_data(reading_type=reading_type)
            await message.answer(
                f"Расклад: {label}\n\nНапиши свой вопрос обычным сообщением — я сделаю расклад и объясню карты.",
                reply_markup=inline_reading_prompt(reading_type),
            )
            return

        await _stream_chat_reply(message, text)
    except Exception as exc:
        await _track(None, "bot.error", {"handler": "message", "error": str(exc)})
        await message.answer("Не удалось обработать сообщение. Попробуй ещё раз.")


async def _handle_menu_text(message: Message, state: FSMContext, text: str) -> None:
    tarot = TarotService()
    await state.clear()

    if text == "Карта дня":
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        prediction, card = await tarot.daily_card_for_telegram(message.from_user.id)
        if card:
            await send_drawn_cards(message, [card])
        await message.answer(prediction, parse_mode=None)
        await _track(None, "bot.daily_card", {"telegram_id": message.from_user.id})
        return

    if text == "Сделать расклад":
        await message.answer(READINGS_MENU_TEXT, reply_markup=inline_readings_menu())
        await _track(None, "bot.menu", {"item": text})
        return

    if text == "История раскладов":
        history_text, readings = await tarot.history_entries(message.from_user.id)
        await message.answer(
            history_text,
            reply_markup=inline_history_menu(readings) if readings else None,
            parse_mode=None,
        )
        await _track(None, "bot.menu", {"item": text})
        return

    if text == "Мой профиль":
        await message.answer(await tarot.profile_extended_for_telegram(message.from_user.id), parse_mode=None)
        await _track(None, "bot.menu", {"item": text})
        return

    if text == "Подписка и баланс":
        await _open_billing(message)
        await _track(None, "bot.menu", {"item": text})
        return

    if text == "Настройки":
        await message.answer(
            await SettingsService().get_panel_text(message.from_user.id),
            reply_markup=inline_settings_menu(),
            parse_mode=None,
        )
        await _track(None, "bot.menu", {"item": text})
        return


def register_handlers(dispatcher: Dispatcher) -> None:
    dispatcher.include_router(router)
