"""Deliver scheduled notifications with Leia images and keyboards."""

from __future__ import annotations

from aiogram import Bot

from app.bot.formatting import to_telegram_html
from app.bot.leia_assets import leia_asset_path
from app.bot.leia_keyboards import inline_packages_menu, inline_referral_share
from app.database.models import Notification, User
from app.services.telegram_notify import send_bot_html, send_bot_photo


def _reply_markup(payload: dict):
    keyboard = payload.get("keyboard")
    if keyboard == "packages":
        return inline_packages_menu()
    if keyboard == "referral_share":
        link = str(payload.get("link", "")).strip()
        if link:
            return inline_referral_share(link)
    return None


async def deliver_notification(bot: Bot, user: User, notification: Notification) -> bool:
    if not isinstance(notification.payload, dict):
        return False
    payload = notification.payload
    text = str(payload.get("text", "")).strip()
    if not text or user.is_blocked:
        return False

    reply_markup = _reply_markup(payload)
    html = to_telegram_html(text)
    image_key = payload.get("image_key")
    if image_key:
        asset = leia_asset_path(str(image_key))
        if asset:
            return await send_bot_photo(
                bot,
                user.telegram_id,
                str(asset),
                caption_html=html,
                caption_plain=text,
                reply_markup=reply_markup,
            )

    return await send_bot_html(bot, user.telegram_id, html, reply_markup=reply_markup)
