from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.leia_texts import REFERRAL_INVITE_AFTER_PURCHASE
from app.database.models import Notification, Payment, User
from app.services.referrals.service import ReferralService

_INVITE_KIND = "referral_invite_friend"
_INVITE_DELAY_DAYS = 3


def _qualifies_for_invite(purpose: str) -> bool:
    if purpose.startswith("product_") and purpose.endswith("_full"):
        return True
    return purpose in {
        "combo_happy_woman",
        "subscription_love_plus",
        "subscription_vip",
    }


async def schedule_friend_invite(
    session: AsyncSession,
    user: User,
    payment: Payment,
    *,
    bot_username: str | None = None,
) -> None:
    if not _qualifies_for_invite(payment.purpose):
        return

    existing = await session.scalar(
        select(Notification.id).where(
            Notification.user_id == user.id,
            Notification.kind == _INVITE_KIND,
        )
    )
    if existing:
        return

    username = (bot_username or "astro_leia_bot").lstrip("@")
    link = ReferralService().build_referral_link(username, user.telegram_id)
    text = REFERRAL_INVITE_AFTER_PURCHASE.format(link=link)
    scheduled = datetime.now(UTC) + timedelta(days=_INVITE_DELAY_DAYS)
    session.add(
        Notification(
            user_id=user.id,
            kind=_INVITE_KIND,
            scheduled_at=scheduled,
            payload={
                "text": text,
                "image_key": "referral",
                "keyboard": "referral_share",
                "link": link,
            },
        )
    )
