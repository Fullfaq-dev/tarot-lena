from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import Bot
from sqlalchemy import select

from app.core.config import get_settings
from app.database.models import BalanceTransaction, User
from app.database.session import AsyncSessionLocal
from app.services.billing.limits import CHANNEL_GIFT_RUB

logger = logging.getLogger(__name__)

_SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}


async def is_channel_member(bot: Bot, telegram_id: int) -> bool:
    """Return True if the user is subscribed to the gift channel.

    Requires the bot to be a member/admin of the channel; otherwise
    get_chat_member fails and we treat the user as not subscribed.
    """
    settings = get_settings()
    try:
        member = await bot.get_chat_member(settings.gift_channel_chat_id, telegram_id)
    except Exception as exc:
        logger.warning("get_chat_member failed for %s: %s", telegram_id, exc)
        return False
    status = getattr(member.status, "value", member.status)
    return str(status) in _SUBSCRIBED_STATUSES


class GiftService:
    async def is_available(self, telegram_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            return bool(user) and not user.gift_claimed

    async def claim(self, telegram_id: int) -> tuple[bool, Decimal]:
        """Credit the one-time gift atomically. Returns (granted_now, amount)."""
        amount = CHANNEL_GIFT_RUB
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None or user.gift_claimed:
                return False, amount
            user.gift_claimed = True
            user.balance_rub += amount
            session.add(
                BalanceTransaction(
                    user_id=user.id,
                    amount_rub=amount,
                    reason="channel_gift",
                )
            )
            await session.commit()
            return True, amount
