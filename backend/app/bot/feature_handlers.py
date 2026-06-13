"""Handlers for Zen mode and Runes/Stones/Bracelet features."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.helpers import safe_callback_answer, safe_edit
from app.bot.i18n import t
from app.bot.keyboards import (
    inline_bracelet_prompt,
    inline_energy_menu,
    inline_rune_prompt,
    inline_stone_prompt,
    inline_zen_menu,
    inline_zen_prompt,
)
from app.bot.states import BotStates
from app.bot.streaming import stream_to_message
from app.services.ai.orchestrator import AIOrchestrator
from app.services.energy.service import EnergyService
from app.services.onboarding.service import OnboardingService
from app.services.settings.service import SettingsService
from app.services.zen.service import ZenService

logger = logging.getLogger(__name__)
router = Router()


async def _lang(telegram_id: int) -> str:
    return await SettingsService().get_ui_language(telegram_id)


async def _require_onboarded(callback: CallbackQuery) -> bool:
    if await OnboardingService().is_onboarded(callback.from_user):
        return True
    await callback.message.answer(t("onboarding_gate", await _lang(callback.from_user.id)))
    return False


@router.callback_query(F.data == "nav:zen")
async def nav_zen(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    if not await _require_onboarded(callback):
        return
    await state.clear()
    lang = await _lang(callback.from_user.id)
    await safe_edit(callback.message, t("zen_menu_text", lang), inline_zen_menu(lang))


@router.callback_query(F.data == "nav:zen:daily")
async def nav_zen_daily(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    if not await _require_onboarded(callback):
        return
    lang = await _lang(callback.from_user.id)
    zen = ZenService()
    prompt = zen.daily_prompt(lang)
    text = f"{zen.daily_intro(lang)}\n\n**{prompt}**"
    await state.set_state(BotStates.waiting_zen_question)
    await state.update_data(zen_mode="daily")
    await safe_edit(callback.message, text, inline_zen_prompt(lang))


@router.callback_query(F.data == "nav:zen:ask")
async def nav_zen_ask(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    if not await _require_onboarded(callback):
        return
    lang = await _lang(callback.from_user.id)
    await state.set_state(BotStates.waiting_zen_question)
    await state.update_data(zen_mode="ask")
    await safe_edit(callback.message, t("zen_ask_prompt", lang), inline_zen_prompt(lang))


@router.callback_query(F.data == "nav:energy")
async def nav_energy(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    if not await _require_onboarded(callback):
        return
    await state.clear()
    lang = await _lang(callback.from_user.id)
    await safe_edit(callback.message, t("energy_menu_text", lang), inline_energy_menu(lang))


@router.callback_query(F.data == "nav:energy:runes")
async def nav_energy_runes(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    if not await _require_onboarded(callback):
        return
    lang = await _lang(callback.from_user.id)
    await state.set_state(BotStates.waiting_rune_question)
    await safe_edit(callback.message, t("rune_ask_prompt", lang), inline_rune_prompt(lang))


@router.callback_query(F.data == "nav:energy:stones")
async def nav_energy_stones(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    if not await _require_onboarded(callback):
        return
    lang = await _lang(callback.from_user.id)
    await state.set_state(BotStates.waiting_stone_query)
    await safe_edit(callback.message, t("stone_ask_prompt", lang), inline_stone_prompt(lang))


@router.callback_query(F.data == "nav:energy:bracelet")
async def nav_energy_bracelet(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    if not await _require_onboarded(callback):
        return
    lang = await _lang(callback.from_user.id)
    await state.set_state(BotStates.waiting_bracelet_query)
    await safe_edit(callback.message, t("bracelet_ask_prompt", lang), inline_bracelet_prompt(lang))


async def handle_zen_question(message: Message, text: str, state: FSMContext) -> None:
    lang = await _lang(message.from_user.id)
    try:
        await state.clear()
        orchestrator = AIOrchestrator()
        user_id, messages, error, user_message_id, billing_mode = await orchestrator.prepare_zen_reflection(
            message.from_user, text, lang=lang
        )
        if error:
            await message.answer(error)
            return

        answer = await stream_to_message(message, orchestrator.stream_chat(messages or []))
        await orchestrator.complete_chat(
            user_id or "",
            text,
            answer,
            user_message_id=user_message_id,
            context_messages=messages,
            feature="zen_reflection",
            billing_mode=billing_mode,
        )
    except Exception as exc:
        logger.exception("Zen reflection failed: %s", exc)
        await message.answer(t("error_process_message", lang))


async def handle_rune_question(message: Message, text: str, state: FSMContext) -> None:
    lang = await _lang(message.from_user.id)
    try:
        await state.clear()
        energy = EnergyService()
        drawn = energy.draw_runes(3)
        rune_text = energy.format_runes_text(drawn, lang)
        prefix = f"{t('rune_result_header', lang)}\n{rune_text}\n\n"

        orchestrator = AIOrchestrator()
        user_id, messages, error, user_message_id, billing_mode = await orchestrator.prepare_rune_reading(
            message.from_user, text, drawn, lang=lang
        )
        if error:
            await message.answer(error)
            return

        answer = await stream_to_message(message, orchestrator.stream_chat(messages or []), prefix=prefix)
        await orchestrator.complete_chat(
            user_id or "",
            text,
            f"{prefix}{answer}".strip(),
            user_message_id=user_message_id,
            context_messages=messages,
            feature="rune_reading",
            billing_mode=billing_mode,
        )
    except Exception as exc:
        logger.exception("Rune reading failed: %s", exc)
        await message.answer(t("error_process_message", lang))


async def handle_stone_query(message: Message, text: str, state: FSMContext) -> None:
    lang = await _lang(message.from_user.id)
    try:
        await state.clear()
        orchestrator = AIOrchestrator()

        await message.bot.send_chat_action(message.chat.id, "typing")
        user_id, stones, pick_reason, messages, error, user_message_id, billing_mode, pick_usage = (
            await orchestrator.prepare_stone_reading(message.from_user, text, lang=lang)
        )
        if error:
            await message.answer(error)
            return

        energy = EnergyService()
        stone_text = energy.format_stones_text(stones, lang)
        prefix = f"{t('stone_result_header', lang)}\n{stone_text}"
        if pick_reason:
            prefix += f"\n_{pick_reason}_"
        prefix += "\n\n"

        answer = await stream_to_message(message, orchestrator.stream_chat(messages or []), prefix=prefix)
        await orchestrator.complete_chat(
            user_id or "",
            text,
            f"{prefix}{answer}".strip(),
            user_message_id=user_message_id,
            context_messages=messages,
            feature="stone_reading",
            billing_mode=billing_mode,
            extra_api_usage=pick_usage,
        )
    except Exception as exc:
        logger.exception("Stone reading failed: %s", exc)
        await message.answer(t("error_process_message", lang))


async def handle_bracelet_query(message: Message, text: str, state: FSMContext) -> None:
    lang = await _lang(message.from_user.id)
    try:
        await state.clear()
        orchestrator = AIOrchestrator()

        await message.bot.send_chat_action(message.chat.id, "typing")
        user_id, slots, pick_reason, messages, error, user_message_id, billing_mode, pick_usage = (
            await orchestrator.prepare_bracelet_reading(message.from_user, text, lang=lang)
        )
        if error:
            await message.answer(error)
            return

        energy = EnergyService()
        layout_text = energy.format_bracelet_text(slots, lang)
        prefix = f"{t('bracelet_result_header', lang)}\n{layout_text}"
        if pick_reason:
            prefix += f"\n_{pick_reason}_"
        prefix += "\n\n"

        answer = await stream_to_message(message, orchestrator.stream_chat(messages or []), prefix=prefix)
        await orchestrator.complete_chat(
            user_id or "",
            text,
            f"{prefix}{answer}".strip(),
            user_message_id=user_message_id,
            context_messages=messages,
            feature="bracelet_reading",
            billing_mode=billing_mode,
            extra_api_usage=pick_usage,
        )
    except Exception as exc:
        logger.exception("Bracelet reading failed: %s", exc)
        await message.answer(t("error_process_message", lang))
