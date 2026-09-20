from __future__ import annotations

import secrets
from datetime import UTC, datetime

from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.models import (
    AnalyticsEvent,
    BalanceTransaction,
    DailyPrediction,
    GeneratedReport,
    MediaJob,
    Memory,
    Message,
    Notification,
    NotificationLog,
    OnboardingSession,
    Payment,
    ProductEntitlement,
    ProductUsage,
    Referral,
    ReferralWithdrawalRequest,
    SoulProfile,
    Subscription,
    TarotReading,
    UsageRecord,
    User,
    UserSettings,
    VoiceMessage,
    WebIdentity,
    WebSession,
)
from app.services.web.service import guest_telegram_id

BIND_TTL = 900
_redis: Redis | None = None


async def _r() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def create_bind_link(user: User) -> dict:
    bot = get_settings().telegram_bot_username.lstrip("@")
    if user.telegram_id and user.telegram_id > 0:
        return {
            "bound": True,
            "telegram_id": user.telegram_id,
            "username": user.username,
        }
    token = secrets.token_urlsafe(18)
    await (await _r()).setex(f"web:tgbind:{token}", BIND_TTL, user.id)
    return {
        "bound": False,
        "url": f"https://t.me/{bot}?start=bind_{token}",
        "expires_sec": BIND_TTL,
    }


async def consume_bind_token(session: AsyncSession, token: str, telegram_user: User) -> User:
    raw = await (await _r()).get(f"web:tgbind:{token}")
    if not raw:
        raise ValueError("Ссылка истекла. Открой кабинет на сайте и нажми «Привязать Telegram» ещё раз.")
    site = await session.scalar(select(User).where(User.id == raw))
    if site is None:
        raise ValueError("Аккаунт на сайте не найден")
    merged = await merge_site_and_telegram(session, site=site, telegram_user=telegram_user)
    await (await _r()).delete(f"web:tgbind:{token}")
    return merged


async def merge_site_and_telegram(session: AsyncSession, *, site: User, telegram_user: User) -> User:
    real_tid = int(telegram_user.telegram_id)
    if real_tid <= 0:
        raise ValueError("Это не Telegram-аккаунт")
    if site.id == telegram_user.id:
        if site.telegram_id != real_tid:
            site.telegram_id = real_tid
        if telegram_user.username:
            site.username = telegram_user.username
        return site
    if site.telegram_id and site.telegram_id > 0 and site.telegram_id != real_tid:
        raise ValueError("Этот кабинет уже привязан к другому Telegram")

    keep, donor = site, telegram_user

    for model in (UserSettings, SoulProfile):
        keep_row = await session.scalar(select(model).where(model.user_id == keep.id))
        donor_row = await session.scalar(select(model).where(model.user_id == donor.id))
        if donor_row and keep_row:
            await session.delete(donor_row)
        elif donor_row:
            donor_row.user_id = keep.id

    keep_sub = await session.scalar(select(Subscription).where(Subscription.user_id == keep.id))
    donor_sub = await session.scalar(select(Subscription).where(Subscription.user_id == donor.id))
    ranks = {"free": 0, "plus": 1, "premium": 2}
    if donor_sub and keep_sub:
        d_rank = ranks.get(donor_sub.tier, 0)
        k_rank = ranks.get(keep_sub.tier, 0)
        d_exp = donor_sub.expires_at or datetime.min.replace(tzinfo=UTC)
        k_exp = keep_sub.expires_at or datetime.min.replace(tzinfo=UTC)
        if d_rank > k_rank or (d_rank == k_rank and d_exp > k_exp):
            keep_sub.tier = donor_sub.tier
            keep_sub.status = donor_sub.status
            keep_sub.expires_at = donor_sub.expires_at
            keep_sub.started_at = donor_sub.started_at
            keep_sub.provider = donor_sub.provider
            keep_sub.provider_subscription_id = donor_sub.provider_subscription_id
        await session.delete(donor_sub)
    elif donor_sub:
        donor_sub.user_id = keep.id

    keep_onb = await session.scalar(select(OnboardingSession).where(OnboardingSession.user_id == keep.id))
    if keep_onb is None:
        await session.execute(
            update(OnboardingSession).where(OnboardingSession.user_id == donor.id).values(user_id=keep.id)
        )

    for ident in list((await session.scalars(select(WebIdentity).where(WebIdentity.user_id == donor.id))).all()):
        clash = await session.scalar(
            select(WebIdentity).where(
                WebIdentity.user_id == keep.id,
                WebIdentity.provider == ident.provider,
                WebIdentity.subject == ident.subject,
            )
        )
        if clash:
            await session.delete(ident)
        else:
            ident.user_id = keep.id

    for row in list((await session.scalars(select(DailyPrediction).where(DailyPrediction.user_id == donor.id))).all()):
        clash = await session.scalar(
            select(DailyPrediction).where(
                DailyPrediction.user_id == keep.id,
                DailyPrediction.prediction_date == row.prediction_date,
            )
        )
        if clash:
            await session.delete(row)
        else:
            row.user_id = keep.id

    donor_as_referred = await session.scalar(select(Referral).where(Referral.referred_user_id == donor.id))
    keep_as_referred = await session.scalar(select(Referral).where(Referral.referred_user_id == keep.id))
    if donor_as_referred and keep_as_referred:
        await session.delete(donor_as_referred)
    elif donor_as_referred:
        donor_as_referred.referred_user_id = keep.id
    await session.execute(
        update(Referral).where(Referral.referrer_user_id == donor.id).values(referrer_user_id=keep.id)
    )

    for model in (
        Message,
        Memory,
        Payment,
        ProductEntitlement,
        ProductUsage,
        TarotReading,
        VoiceMessage,
        Notification,
        NotificationLog,
        UsageRecord,
        BalanceTransaction,
        GeneratedReport,
        ReferralWithdrawalRequest,
        MediaJob,
        AnalyticsEvent,
        WebSession,
    ):
        await session.execute(update(model).where(model.user_id == donor.id).values(user_id=keep.id))

    keep.balance_rub = (keep.balance_rub or 0) + (donor.balance_rub or 0)
    donor.balance_rub = 0
    if donor.username:
        keep.username = donor.username
    if donor.is_onboarded:
        keep.is_onboarded = True
    keep.first_name = keep.first_name or donor.first_name
    keep.last_name = keep.last_name or donor.last_name

    donor.telegram_id = guest_telegram_id(f"merged:{donor.id}")
    await session.flush()
    keep.telegram_id = real_tid
    await session.flush()
    return keep
