"""Старт бота по ссылке с сайта: мини целиком и один бесплатный вопрос."""

from __future__ import annotations

import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from app.bot.states import BotStates
from app.core.config import get_settings
from app.database.models import WebReading, WebSession
from app.database.session import AsyncSessionLocal
from app.services.ai.kie_client import KieClient
from app.services.web.mini import mini_plain

logger = logging.getLogger(__name__)


def _pay_url(token: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/r/{token}?pay=1"


def _pay_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть полный разбор", url=_pay_url(token))]
        ]
    )


async def handle_web_start(message: Message, token: str, user_id: str | None, state: FSMContext) -> bool:
    try:
        async with AsyncSessionLocal() as db:
            reading = await db.scalar(select(WebReading).where(WebReading.token == token))
            if reading is None:
                return False
            web = await db.scalar(select(WebSession).where(WebSession.id == reading.session_id))
            if web and user_id:
                web.user_id = user_id
                await db.commit()
            text = mini_plain(reading.mini or {}) or "Разбор с сайта сохранён."
            already = bool((reading.input_payload or {}).get("tg_free_asked"))
            logger.info("bot web_start token=%s card=%s", token, reading.card_id)
    except Exception:
        logger.exception("web reading start failed")
        return False

    await message.answer(text[:3500], parse_mode=None)
    if already:
        await message.answer(
            "Полный разбор открывается на сайте.",
            reply_markup=_pay_keyboard(token),
            parse_mode=None,
        )
        await state.clear()
        return True
    await message.answer("Задай мне вопрос по этому разбору, отвечу бесплатно.", parse_mode=None)
    await state.set_state(BotStates.waiting_web_mini_question)
    await state.update_data(web_token=token)
    return True


async def handle_web_free_question(message: Message, text: str, state: FSMContext) -> bool:
    data = await state.get_data()
    token = str(data.get("web_token") or "")
    if not token:
        await state.clear()
        return False
    from sqlalchemy.orm.attributes import flag_modified

    async with AsyncSessionLocal() as db:
        reading = await db.scalar(select(WebReading).where(WebReading.token == token))
        if reading is None:
            await state.clear()
            await message.answer("Ссылка на разбор уже не работает.", parse_mode=None)
            return True
        payload = dict(reading.input_payload or {})
        if payload.get("tg_free_asked"):
            await state.clear()
            await message.answer(
                "Бесплатный вопрос по этому разбору уже был.",
                reply_markup=_pay_keyboard(token),
                parse_mode=None,
            )
            return True
        mini = mini_plain(reading.mini or {})
        answers = reading.answers or []
        drawn = (reading.input_payload or {}).get("drawn") or []
        prompt = (
            "Ты Лея. Ответь на один вопрос по мини-разбору с сайта. "
            "Коротко, на «ты», без нового расклада. До 800 знаков.\n\n"
            f"Мини:\n{mini}\n\n"
            f"Ответы квиза: {answers}\n"
            f"Карты: {[item.get('name') for item in drawn]}\n"
            f"Дата: {(reading.input_payload or {}).get('birth')}\n"
            f"Вопрос: {text}"
        )
        try:
            reply = await KieClient().chat_completion(
                [{"role": "user", "content": prompt}],
                reasoning_effort="none",
                model=get_settings().openai_mini_model,
                max_output_tokens=400,
                max_attempts=1,
            )
        except Exception:
            logger.exception("web tg free question failed")
            reply = "Не получилось ответить сейчас. Открой разбор на сайте - он сохранён."
        reply = (reply or "").strip()
        if len(reply) > 800:
            reply = reply[:797].rstrip(" .,;") + "…"
        payload["tg_free_asked"] = True
        reading.input_payload = payload
        flag_modified(reading, "input_payload")
        await db.commit()

    await message.answer(reply, parse_mode=None)
    await message.answer(
        "Полный разбор открывается на сайте.",
        reply_markup=_pay_keyboard(token),
        parse_mode=None,
    )
    await state.clear()
    return True
