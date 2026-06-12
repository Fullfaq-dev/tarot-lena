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

from app.bot.cards_media import send_card_with_caption, send_drawn_cards
from app.bot.media import send_photo_from_url
from app.bot.formatting import to_telegram_html
from app.core.config import get_settings
from app.bot.helpers import clear_processing_placeholder, safe_callback_answer, safe_edit, send_processing_placeholder
from app.bot.keyboards import (
    MAIN_MENU_TEXT,
    MENU_ACTIONS,
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
    inline_profile_menu,
    inline_reading_prompt,
    inline_readings_menu,
    inline_referral_menu,
    inline_settings_menu,
    inline_withdraw_wallet_menu,
    is_balance_button,
    main_menu,
    onboarding_keyboard,
    profile_field_keyboard,
)
from app.bot.states import BotStates
from app.bot.streaming import chat_action_loop, truncate_text, typing_loop
from app.database.models import Subscription, User, UserSettings
from app.database.session import AsyncSessionLocal
from app.services.ai.orchestrator import AIOrchestrator
from app.services.analytics.tracker import track_event
from app.services.billing.limits import (
    FREE_CHAT_MESSAGES_PER_MONTH,
    can_use_premium_voice,
    free_messages_left,
)
from app.services.billing.tokens import format_balance
from app.services.billing.service import BillingService
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
from app.bot.audio_media import send_voice_from_url

router = Router()
logger = logging.getLogger(__name__)


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


async def _user_main_menu(telegram_id: int):
    balance = await BillingService().get_balance_label(telegram_id)
    return main_menu(balance)


async def _open_billing(message: Message, *, edit_message: Message | None = None) -> None:
    text = await BillingService().panel_text(message.from_user.id)
    markup = inline_billing_menu()
    if edit_message is not None:
        await safe_edit(edit_message, text, markup)
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
    bot_user = await message.bot.get_me()
    text = await ReferralService().panel_text(actor_id, bot_username=bot_user.username)
    share_link = ReferralService().build_referral_link(bot_user.username, actor_id)
    markup = inline_referral_menu(share_link=share_link)
    if edit_message is not None:
        await safe_edit(edit_message, text, markup)
    else:
        await message.answer(text, reply_markup=markup, parse_mode=None)


async def _with_typing(message: Message, coro):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    return await coro


async def _answer_formatted(message: Message, text: str, *, prefix: str = "") -> None:
    body = f"{prefix}{text}"
    html = truncate_text(to_telegram_html(body))
    try:
        await message.answer(html, parse_mode=ParseMode.HTML)
    except Exception:
        await message.answer(truncate_text(body), parse_mode=None)


async def _generate_with_typing(message: Message, coro):
    stop = asyncio.Event()
    typing_task = asyncio.create_task(typing_loop(message.bot, message.chat.id, stop))
    try:
        return await coro
    finally:
        stop.set()
        await typing_task


async def _send_daily_card(message: Message, telegram_id: int) -> None:
    tarot = TarotService()
    interpretation, card = await _generate_with_typing(
        message,
        tarot.daily_card_for_telegram(telegram_id),
    )
    if interpretation.startswith("Сначала нажми /start"):
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


async def _handle_reading_question(message: Message, state: FSMContext, question: str) -> None:
    data = await state.get_data()
    reading_type = data.get("reading_type", "past_present_future")
    await state.clear()

    user_id = await _get_user_id(message.from_user.id)
    if user_id is None:
        await message.answer("Сначала нажми /start, чтобы создать твой профиль.")
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

    interpretation = await _generate_with_typing(
        message,
        orchestrator.generate_chat(messages or []),
    )
    if not interpretation or "cannot fulfill" in interpretation.lower():
        interpretation = tarot.interpret_locally(question, cards)

    await _answer_formatted(message, interpretation, prefix=prefix)

    usage = await orchestrator.complete_chat(
        user_db_id or user_id,
        question,
        interpretation,
        user_message_id=user_message_id,
        context_messages=messages,
        feature="tarot_reading",
        billing_mode=billing_mode,
    )
    await _notify_billing(
        message,
        billing_mode,
        usage,
        reply_markup=await _user_main_menu(message.from_user.id),
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
) -> bool:
    user_telegram_id = telegram_id or (message.from_user.id if message.from_user else 0)
    charged = Decimal(str(usage.get("charged_rub", "0")))
    image_charged = Decimal(str(usage.get("image_charged_rub", "0")))
    if charged > 0:
        parts = [f"Списано {charged} ₽"]
        if image_charged > 0:
            parts.append(f"включая инфографику {image_charged} ₽")
        parts.append(f"Остаток на балансе: {format_balance(usage.get('balance_after'))}.")
        await message.answer(" ".join(parts), reply_markup=reply_markup)
        return True
    if billing_mode == "free" and free_messages_left(
        (await _get_user_free_used(user_telegram_id))
    ) == 0:
        await message.answer(
            f"Это было последнее бесплатное сообщение в этом месяце ({FREE_CHAT_MESSAGES_PER_MONTH}). "
            "Дальше ответы списываются с баланса — пополни его в разделе «Баланс».",
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
        try:
            await message.answer(
                "Обработка фото прервалась. Попробуй отправить снимок ещё раз ✨"
            )
        except Exception:
            pass
    except Exception as exc:
        await _track(None, "bot.error", {"handler": "photo", "error": str(exc)})
        await message.answer(f"Не удалось обработать фото: {exc}")


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
    if actor is None:
        await message.answer("Не получилось определить профиль Telegram. Попробуй ещё раз.")
        return

    user_id = await _get_user_id(actor.id)
    if user_id is None:
        await message.answer("Сначала нажми /start, чтобы создать твой профиль.")
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
                    "Инфографика сгенерирована, но не удалось отправить изображение. Попробуй ещё раз.",
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


async def _chat_reply(message: Message, text: str) -> None:
    orchestrator = AIOrchestrator()
    user_id, messages, error, user_message_id, billing_mode = await orchestrator.prepare_chat(
        message.from_user, text
    )
    if error:
        await message.answer(error)
        return

    if billing_mode == "balance":
        await message.answer("Бесплатные сообщения закончились. Ответ спишется с баланса.")

    try:
        answer = await _generate_with_typing(
            message,
            orchestrator.generate_chat(messages or []),
        )
        await _answer_formatted(message, answer)
    except Exception as exc:
        logger.exception("Chat reply failed")
        await _track(
            user_id,
            "bot.error",
            {"handler": "chat_reply", "error": str(exc), "traceback": traceback.format_exc()[-2000:]},
        )
        await message.answer("Не удалось получить ответ от модели. Попробуй ещё раз через минуту.")
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
                text = (
                    f"{text}\n\n"
                    f"Тебя пригласил(а) {referrer_name}. Спасибо, что пришёл по рекомендации ✨"
                )

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


@router.callback_query(F.data == "ref:share")
async def referral_share_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    bot_user = await callback.message.bot.get_me()
    link = ReferralService().build_referral_link(bot_user.username, callback.from_user.id)
    await callback.message.answer(
        f"🔗 Твоя личная ссылка:\n{link}\n\n"
        "Перешли её другу — с каждой его или её оплаты тебе будет приходить 40% на реферальный баланс. 💰",
        reply_markup=inline_referral_menu(share_link=link),
    )


async def _referral_available(telegram_id: int) -> Decimal | None:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return None
        stats = await ReferralService().get_stats(session, user)
        return stats["available"]


@router.callback_query(F.data == "ref:withdraw")
async def referral_withdraw_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    available = await _referral_available(callback.from_user.id)
    if available is None:
        await callback.message.answer("Сначала нажми /start.")
        return
    if available < MIN_WITHDRAWAL_RUB:
        await callback.message.answer(
            f"💸 Вывод доступен от {format_balance(MIN_WITHDRAWAL_RUB)}.\n"
            f"Сейчас на балансе: {format_balance(available)}.\n\n"
            "Приглашай друзей по своей ссылке — 40% с каждой их оплаты твои. ✨"
        )
        return

    await state.set_state(BotStates.waiting_withdrawal_amount)
    await callback.message.answer(
        f"💰 Доступно к выводу: {format_balance(available)}\n\n"
        f"Напиши сумму в рублях, которую хочешь вывести (от {format_balance(MIN_WITHDRAWAL_RUB)}), "
        "или нажми кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"💸 Вывести всё ({format_balance(available)})",
                        callback_data="ref:amount_all",
                    )
                ],
                [InlineKeyboardButton(text="🏠 На главную", callback_data="nav:back:main")],
            ]
        ),
    )


async def _ask_withdrawal_wallet(message: Message, state: FSMContext, telegram_id: int) -> None:
    saved_wallet = await ReferralService().get_saved_wallet(telegram_id)
    if saved_wallet:
        await state.set_state(BotStates.waiting_withdrawal_wallet)
        await message.answer(
            "💼 Куда отправить USDT (сеть TRC-20)?\n\n"
            f"У тебя сохранён кошелёк: {saved_wallet}",
            reply_markup=inline_withdraw_wallet_menu(saved_wallet),
        )
        return
    await state.set_state(BotStates.waiting_withdrawal_wallet)
    await message.answer(
        "💼 Пришли адрес своего USDT-кошелька в сети TRC-20.\n\n"
        "Он начинается с буквы «T» и состоит из 34 символов. "
        "Я сохраню его — в следующий раз вводить не придётся."
    )


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
    await callback.answer()
    available = await _referral_available(callback.from_user.id)
    if available is None or available < MIN_WITHDRAWAL_RUB:
        await state.clear()
        await callback.message.answer("Недостаточно средств для вывода.")
        return
    await state.update_data(withdrawal_amount=str(available))
    await _ask_withdrawal_wallet(callback.message, state, callback.from_user.id)


@router.callback_query(F.data == "ref:wallet_saved")
async def referral_wallet_saved_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    wallet = await ReferralService().get_saved_wallet(callback.from_user.id)
    if not wallet:
        await callback.message.answer("Сохранённый кошелёк не найден. Пришли адрес сообщением.")
        return
    await _finish_withdrawal(callback.message, state, callback.from_user.id, wallet)


@router.callback_query(F.data == "ref:wallet_new")
async def referral_wallet_new_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(BotStates.waiting_withdrawal_wallet)
    await callback.message.answer(
        "✏️ Пришли новый адрес USDT-кошелька (сеть TRC-20).\n"
        "Он начинается с «T» и состоит из 34 символов."
    )


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
        await callback.message.answer(text, reply_markup=await _user_main_menu(callback.from_user.id))
        return

    if action == "sub":
        text = await billing.create_subscription_for_telegram(callback.from_user.id, value)
        await callback.message.answer(text, reply_markup=await _user_main_menu(callback.from_user.id))
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
        await _send_daily_card(callback.message, callback.from_user.id)
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
        await safe_edit(callback.message, text, inline_profile_menu(), parse_mode=None)
        await _track(None, "bot.menu", {"item": "profile"})
        return

    if action == "billing":
        text = await BillingService().panel_text(callback.from_user.id)
        await safe_edit(callback.message, text, inline_billing_menu())
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
    await safe_callback_answer(callback)
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
            await source.message.answer(
                "🌅 А вот твоя первая карта дня — бесплатный подарок за знакомство ✨"
            )
            await _send_daily_card(source.message, telegram_user.id)
            await source.message.answer(MAIN_MENU_TEXT, reply_markup=inline_main_menu())
        elif edit:
            await safe_edit(source.message, reply_text, markup)
        else:
            await source.message.answer(reply_text, reply_markup=markup)
    else:
        if completed:
            await source.answer(onboarding_reply, reply_markup=await _user_main_menu(telegram_user.id))
            await source.answer(
                "🌅 А вот твоя первая карта дня — бесплатный подарок за знакомство ✨"
            )
            await _send_daily_card(source, telegram_user.id)
            await source.answer(MAIN_MENU_TEXT, reply_markup=inline_main_menu())
        else:
            await source.answer(reply_text, reply_markup=markup)

    event = "bot.onboarding_complete" if completed else "bot.onboarding_step"
    await _track(user_id, event, {"text": answer[:200]})


async def _user_voice_settings(telegram_id: int) -> tuple[str, str]:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            return "free", "female_mystical"
        subscription = await session.scalar(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        settings = await session.scalar(
            select(UserSettings).where(UserSettings.user_id == user.id)
        )
        tier = subscription.tier if subscription else "free"
        preset = settings.voice_preset if settings else "female_mystical"
        return tier, preset


@router.message(F.voice)
async def voice_message(message: Message) -> None:
    if message.voice is None or message.from_user is None:
        return

    onboarding = OnboardingService()
    if not await onboarding.is_onboarded(message.from_user):
        await message.answer("Сначала давай закончим анкету — ответь на последний вопрос или нажми /start.")
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
            await message.answer("Бесплатные сообщения закончились. Ответ спишется с баланса.")

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
                await message.answer("Не удалось отправить голосовой файл.")
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
            await message.answer(f"Не удалось обработать голосовое: {detail}")
        else:
            await message.answer("Не удалось обработать голосовое. Попробуй ещё раз или напиши текстом.")
    finally:
        await clear_processing_placeholder(status_msg)


@router.message(F.photo)
async def photo_message(message: Message, state: FSMContext) -> None:
    try:
        onboarding = OnboardingService()
        if not await onboarding.is_onboarded(message.from_user):
            await message.answer("Сначала давай закончим анкету — ответь на последний вопрос или нажми /start.")
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
            "📸 Фото получено! Что хочешь узнать?\n"
            "Аура и ладонь — с инфографикой, 100 ₽ с баланса.",
            reply_markup=inline_photo_mode_menu(),
        )
    except Exception as exc:
        await _track(None, "bot.error", {"handler": "photo_message", "error": str(exc)})
        await message.answer("Не удалось принять фото. Попробуй отправить ещё раз.")


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

        if current_state == BotStates.waiting_withdrawal_amount.state:
            amount = parse_withdrawal_amount(text or "")
            if amount is None:
                await message.answer("Напиши сумму числом, например: 3500")
                return
            if amount < MIN_WITHDRAWAL_RUB:
                await message.answer(
                    f"Минимальная сумма вывода — {format_balance(MIN_WITHDRAWAL_RUB)}. "
                    "Напиши сумму побольше 🙂"
                )
                return
            available = await _referral_available(message.from_user.id)
            if available is None or amount > available:
                await message.answer(
                    f"Недостаточно средств. Доступно: {format_balance(available or Decimal('0'))}. "
                    "Напиши сумму поменьше."
                )
                return
            await state.update_data(withdrawal_amount=str(amount))
            await _ask_withdrawal_wallet(message, state, message.from_user.id)
            return

        if current_state == BotStates.waiting_withdrawal_wallet.state:
            wallet = (text or "").strip()
            if not is_valid_trc20_wallet(wallet):
                await message.answer(
                    "Это не похоже на адрес USDT TRC-20. 🤔\n"
                    "Он начинается с «T» и состоит из 34 символов. Проверь и пришли ещё раз."
                )
                return
            await _finish_withdrawal(message, state, message.from_user.id, wallet)
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

        if not text:
            return

        await _chat_reply(message, text)
    except Exception as exc:
        logger.exception("fallback_message failed")
        await _track(
            None,
            "bot.error",
            {"handler": "message", "error": str(exc), "traceback": traceback.format_exc()[-2000:]},
        )
        await message.answer("Не удалось обработать сообщение. Попробуй ещё раз.")


async def _handle_menu_text(message: Message, state: FSMContext, text: str) -> None:
    tarot = TarotService()
    await state.clear()
    action = MENU_ACTIONS.get(text)

    if action == "daily":
        await _send_daily_card(message, message.from_user.id)
        await _track(None, "bot.daily_card", {"telegram_id": message.from_user.id})
        return

    if action == "readings":
        await message.answer(READINGS_MENU_TEXT, reply_markup=inline_readings_menu())
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "history":
        history_text, readings = await tarot.history_entries(message.from_user.id)
        await message.answer(
            history_text,
            reply_markup=inline_history_menu(readings) if readings else None,
            parse_mode=None,
        )
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "profile":
        await message.answer(
            await tarot.profile_extended_for_telegram(message.from_user.id),
            reply_markup=inline_profile_menu(),
            parse_mode=None,
        )
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "billing":
        await _open_billing(message)
        await _track(None, "bot.menu", {"item": text})
        return

    if action == "settings":
        await message.answer(
            await SettingsService().get_panel_text(message.from_user.id),
            reply_markup=inline_settings_menu(),
            parse_mode=None,
        )
        await _track(None, "bot.menu", {"item": text})
        return


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
    dispatcher.include_router(router)
