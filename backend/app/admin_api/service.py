from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import (
    AnalyticsEvent,
    BalanceTransaction,
    Memory,
    Message,
    NotificationLog,
    OnboardingSession,
    Payment,
    ProductEntitlement,
    ProductUsage,
    Referral,
    ReferralWithdrawalRequest,
    RelationshipPerson,
    SoulProfile,
    Subscription,
    TarotCard,
    TarotReading,
    UsageRecord,
    User,
)


def _dec(value: Decimal | None) -> str:
    amount = Decimal(value or Decimal("0"))
    if amount == 0:
        return "0"
    normalized = amount.normalize()
    return format(normalized, "f")


def _dec_usd(value: Decimal | None) -> str:
    amount = Decimal(value or Decimal("0"))
    if amount == 0:
        return "0"
    return f"{amount:.4f}".rstrip("0").rstrip(".")


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


async def dashboard_stats(session: AsyncSession) -> dict[str, Any]:
    now = datetime.now(UTC)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = await session.scalar(select(func.count()).select_from(User)) or 0
    onboarded = await session.scalar(
        select(func.count()).select_from(User).where(User.is_onboarded.is_(True))
    ) or 0
    readings = await session.scalar(
        select(func.count())
        .select_from(ProductUsage)
        .where(
            ProductUsage.content_preview.isnot(None),
            ProductUsage.content_preview != "",
        )
    ) or 0
    payments_sum = await session.scalar(select(func.coalesce(func.sum(Payment.amount_rub), 0))) or 0
    payments_count = await session.scalar(select(func.count()).select_from(Payment)) or 0

    dau = await session.scalar(
        select(func.count(func.distinct(Message.user_id))).where(Message.created_at >= day_ago)
    ) or 0
    wau = await session.scalar(
        select(func.count(func.distinct(Message.user_id))).where(Message.created_at >= week_ago)
    ) or 0
    mau = await session.scalar(
        select(func.count(func.distinct(Message.user_id))).where(Message.created_at >= month_ago)
    ) or 0

    active_users = await session.scalar(
        select(func.count(func.distinct(Message.user_id))).where(Message.created_at >= week_ago)
    ) or 0
    inactive_users = max(total_users - active_users, 0)

    plus_count = await session.scalar(
        select(func.count()).select_from(Subscription).where(Subscription.tier == "plus")
    ) or 0
    premium_count = await session.scalar(
        select(func.count()).select_from(Subscription).where(Subscription.tier == "premium")
    ) or 0

    active_entitlement = or_(
        ProductEntitlement.expires_at.is_(None),
        ProductEntitlement.expires_at > now,
    )
    vip_count = await session.scalar(
        select(func.count())
        .select_from(ProductEntitlement)
        .where(ProductEntitlement.kind == "vip", active_entitlement)
    ) or 0
    love_plus_count = await session.scalar(
        select(func.count())
        .select_from(ProductEntitlement)
        .where(ProductEntitlement.kind == "love_plus", active_entitlement)
    ) or 0
    combo_sales = await session.scalar(
        select(func.count()).select_from(Payment).where(Payment.purpose == "combo_happy_woman")
    ) or 0
    referred_users = await session.scalar(
        select(func.count()).select_from(Referral)
    ) or 0
    product_usages = await session.scalar(
        select(func.count()).select_from(ProductUsage)
    ) or 0

    pending_withdrawals = await session.scalar(
        select(func.count())
        .select_from(ReferralWithdrawalRequest)
        .where(ReferralWithdrawalRequest.status == "pending")
    ) or 0

    return {
        "users": total_users,
        "onboarded_users": onboarded,
        "readings": readings,
        "payments_count": payments_count,
        "payments_total_rub": _dec(payments_sum if isinstance(payments_sum, Decimal) else Decimal(str(payments_sum))),
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "plus_subscribers": plus_count,
        "premium_subscribers": premium_count,
        "vip_subscribers": vip_count,
        "love_plus_subscribers": love_plus_count,
        "combo_sales": combo_sales,
        "referred_users": referred_users,
        "product_usages": product_usages,
        "pending_withdrawals": pending_withdrawals,
    }


async def token_stats(
    session: AsyncSession,
    *,
    days: int = 30,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    if date_from and date_to:
        since = datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        until = datetime.combine(date_to, datetime.max.time(), tzinfo=UTC)
    else:
        since = datetime.now(UTC) - timedelta(days=days)
        until = datetime.now(UTC)

    rows = await session.execute(
        select(
            cast(UsageRecord.created_at, Date).label("day"),
            func.coalesce(func.sum(UsageRecord.input_units), 0),
            func.coalesce(func.sum(UsageRecord.output_units), 0),
            func.coalesce(func.sum(UsageRecord.provider_cost_usd), 0),
            func.coalesce(func.sum(UsageRecord.charged_rub), 0),
            func.count(),
        )
        .where(UsageRecord.created_at >= since, UsageRecord.created_at <= until)
        .group_by(cast(UsageRecord.created_at, Date))
        .order_by(cast(UsageRecord.created_at, Date))
    )

    daily: list[dict[str, Any]] = []
    total_input = 0
    total_output = 0
    total_cost_usd = Decimal("0")
    total_charged_rub = Decimal("0")
    total_requests = 0

    for day, input_tokens, output_tokens, cost_usd, charged_rub, count in rows.all():
        input_tokens = int(input_tokens)
        output_tokens = int(output_tokens)
        cost_usd = Decimal(str(cost_usd))
        charged_rub = Decimal(str(charged_rub))
        count = int(count)
        total_input += input_tokens
        total_output += output_tokens
        total_cost_usd += cost_usd
        total_charged_rub += charged_rub
        total_requests += count
        daily.append(
            {
                "date": day.isoformat(),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "provider_cost_usd": _dec(cost_usd),
                "charged_rub": _dec(charged_rub),
                "requests": count,
            }
        )

    from app.services.billing.tokens import (
        display_provider_cost_rub,
        display_provider_cost_usd,
        provider_cost_credits,
    )

    total_credits = provider_cost_credits(total_input, total_output)
    display_cost_usd = display_provider_cost_usd(total_cost_usd)
    display_cost_rub = display_provider_cost_rub(total_cost_usd)
    margin_rub = total_charged_rub - display_cost_rub

    for row in daily:
        raw = Decimal(str(row["provider_cost_usd"]))
        row["provider_cost_usd"] = _dec_usd(display_provider_cost_usd(raw))
        row["provider_cost_rub"] = _dec(display_provider_cost_rub(raw))

    # Historical Leia readings were not written to usage_records — estimate from ProductUsage.
    if total_requests == 0:
        from app.services.billing.tokens import estimate_tokens, provider_cost_usd as raw_cost_usd

        usage_rows = await session.scalars(
            select(ProductUsage).where(
                ProductUsage.created_at >= since,
                ProductUsage.created_at <= until,
                ProductUsage.content_preview.isnot(None),
                ProductUsage.content_preview != "",
            )
        )
        by_day: dict[str, dict[str, Any]] = {}
        for row in usage_rows:
            out_tok = estimate_tokens(row.content_preview or "")
            in_tok = max(120, out_tok // 2)
            day_key = row.created_at.astimezone(UTC).date().isoformat() if row.created_at else since.date().isoformat()
            bucket = by_day.setdefault(
                day_key,
                {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "provider_cost_usd": Decimal("0"),
                    "charged_rub": Decimal("0"),
                    "requests": 0,
                },
            )
            bucket["input_tokens"] += in_tok
            bucket["output_tokens"] += out_tok
            bucket["provider_cost_usd"] += raw_cost_usd(in_tok, out_tok)
            bucket["requests"] += 1
            total_input += in_tok
            total_output += out_tok
            total_cost_usd += raw_cost_usd(in_tok, out_tok)
            total_requests += 1
        daily = []
        for day_key in sorted(by_day):
            b = by_day[day_key]
            daily.append(
                {
                    "date": day_key,
                    "input_tokens": b["input_tokens"],
                    "output_tokens": b["output_tokens"],
                    "total_tokens": b["input_tokens"] + b["output_tokens"],
                    "provider_cost_usd": _dec_usd(display_provider_cost_usd(b["provider_cost_usd"])),
                    "provider_cost_rub": _dec(display_provider_cost_rub(b["provider_cost_usd"])),
                    "charged_rub": "0",
                    "requests": b["requests"],
                }
            )
        total_credits = provider_cost_credits(total_input, total_output)
        display_cost_usd = display_provider_cost_usd(total_cost_usd)
        display_cost_rub = display_provider_cost_rub(total_cost_usd)
        margin_rub = total_charged_rub - display_cost_rub

    return {
        "summary": {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "kie_credits": _dec(total_credits),
            "provider_cost_usd": _dec_usd(display_cost_usd),
            "provider_cost_rub": _dec(display_cost_rub),
            "charged_rub": _dec(total_charged_rub),
            "margin_rub": _dec(margin_rub),
            "requests": total_requests,
            "pricing_note": (
                "Себестоимость в дашборде = расчёт × 2 (коррекция к KIE). "
                "Новые запросы Леи пишутся в usage_records; старые разборы — оценка по тексту."
            ),
        },
        "daily": daily,
    }


async def signups_chart(session: AsyncSession, days: int = 30) -> list[dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(
        select(cast(User.created_at, Date).label("day"), func.count())
        .where(User.created_at >= since)
        .group_by(cast(User.created_at, Date))
        .order_by(cast(User.created_at, Date))
    )
    return [{"date": row[0].isoformat(), "count": row[1]} for row in result.all()]


async def list_users(session: AsyncSession, limit: int = 200) -> list[dict[str, Any]]:
    week_ago = datetime.now(UTC) - timedelta(days=7)
    users = await session.scalars(select(User).order_by(User.created_at.desc()).limit(limit))
    items: list[dict[str, Any]] = []
    for user in users:
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        last_msg = await session.scalar(
            select(func.max(Message.created_at)).where(Message.user_id == user.id)
        )
        msg_count = await session.scalar(
            select(func.count()).select_from(Message).where(Message.user_id == user.id)
        ) or 0
        items.append(
            {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_onboarded": user.is_onboarded,
                "is_blocked": user.is_blocked,
                "balance_rub": _dec(user.balance_rub),
                "tier": sub.tier if sub else "free",
                "message_count": msg_count,
                "last_active_at": _dt(last_msg),
                "is_active": bool(last_msg and last_msg >= week_ago),
                "created_at": _dt(user.created_at),
                "referral_reward_percent": user.referral_reward_percent,
            }
        )
    return items


async def user_detail(session: AsyncSession, user_id: str) -> dict[str, Any] | None:
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        return None

    sub = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
    profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
    onboarding = await session.scalar(
        select(OnboardingSession)
        .where(OnboardingSession.user_id == user.id)
        .order_by(OnboardingSession.created_at.desc())
        .limit(1)
    )
    last_msg = await session.scalar(
        select(func.max(Message.created_at)).where(Message.user_id == user.id)
    )
    week_ago = datetime.now(UTC) - timedelta(days=7)

    entitlements_rows = await session.scalars(
        select(ProductEntitlement).where(ProductEntitlement.user_id == user.id)
    )
    usage_rows = await session.scalars(
        select(ProductUsage).where(ProductUsage.user_id == user.id)
    )

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_onboarded": user.is_onboarded,
        "is_blocked": user.is_blocked,
        "balance_rub": _dec(user.balance_rub),
        "free_messages_used_month": user.free_messages_used_month,
        "free_readings_used_month": user.free_readings_used_month,
        "free_limits_month": user.free_limits_month,
        "tier": sub.tier if sub else "free",
        "subscription_status": sub.status if sub else None,
        "subscription_expires_at": _dt(sub.expires_at) if sub else None,
        "is_active": bool(last_msg and last_msg >= week_ago),
        "last_active_at": _dt(last_msg),
        "created_at": _dt(user.created_at),
        "referral_reward_percent": user.referral_reward_percent,
        "soul_profile": _soul_profile_dict(profile) if profile else None,
        "onboarding": {
            "current_step": onboarding.current_step if onboarding else None,
            "answers": onboarding.answers if onboarding else {},
            "completed_at": _dt(onboarding.completed_at) if onboarding else None,
        }
        if onboarding
        else None,
        "entitlements": [
            {
                "kind": row.kind,
                "kind_label": _ENTITLEMENT_KIND_LABELS.get(row.kind, row.kind),
                "expires_at": _dt(row.expires_at),
                "uses_remaining": row.uses_remaining,
            }
            for row in entitlements_rows
        ],
        "product_usages": [
            _product_usage_dict(row) for row in usage_rows
        ],
    }


def _product_title(product_id: str) -> str:
    from app.services.products.catalog import PRODUCTS

    product = PRODUCTS.get(product_id)
    if product:
        return f"{product.emoji} {product.title}"
    return product_id


def _product_usage_dict(row: ProductUsage) -> dict[str, Any]:
    return {
        "id": row.id,
        "product_id": row.product_id,
        "product_title": _product_title(row.product_id),
        "level": row.level,
        "level_label": "мини" if row.level == "mini" else "полная",
        "payment_id": row.payment_id,
        "content_preview": row.content_preview or "",
        "created_at": _dt(row.created_at),
    }


def _soul_profile_dict(profile: SoulProfile) -> dict[str, Any]:
    return {
        "name": profile.name,
        "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
        "birth_time": profile.birth_time,
        "birth_city": profile.birth_city,
        "gender": profile.gender,
        "relationship_status": profile.relationship_status,
        "has_children": profile.has_children,
        "profession": profile.profession,
        "six_month_goal": profile.six_month_goal,
        "main_concern": profile.main_concern,
        "belief_system": profile.belief_system,
        "archetype": profile.archetype,
        "personal_arcana": profile.personal_arcana,
        "strengths": profile.strengths,
        "weaknesses": profile.weaknesses,
        "preferences": profile.preferences,
    }


async def user_messages(session: AsyncSession, user_id: str, limit: int = 2000) -> list[dict[str, Any]]:
    """Full chat timeline: Message rows + historical ProductUsage readings."""
    result = await session.scalars(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    messages = list(result)
    usage_ids_logged = {
        str((m.meta or {}).get("product_usage_id"))
        for m in messages
        if (m.meta or {}).get("product_usage_id")
    }

    usages = await session.scalars(
        select(ProductUsage)
        .where(
            ProductUsage.user_id == user_id,
            ProductUsage.content_preview.isnot(None),
            ProductUsage.content_preview != "",
        )
        .order_by(ProductUsage.created_at.asc())
        .limit(limit)
    )

    items: list[dict[str, Any]] = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "tokens_input": m.tokens_input,
            "tokens_output": m.tokens_output,
            "cost_rub": _dec(m.cost_rub),
            "provider_cost_usd": m.meta.get("provider_cost_usd") if m.meta else None,
            "meta": m.meta or {},
            "created_at": _dt(m.created_at),
        }
        for m in messages
    ]
    for row in usages:
        if row.id in usage_ids_logged:
            continue
        product = _product_title(row.product_id)
        level_label = "мини" if row.level == "mini" else "полная"
        items.append(
            {
                "id": f"usage:{row.id}",
                "role": "assistant",
                "content": row.content_preview or "",
                "tokens_input": 0,
                "tokens_output": 0,
                "cost_rub": "0",
                "provider_cost_usd": None,
                "meta": {
                    "source": "product_usage",
                    "product_id": row.product_id,
                    "product_title": product,
                    "level": row.level,
                    "level_label": level_label,
                    "product_usage_id": row.id,
                    "payment_id": row.payment_id,
                },
                "created_at": _dt(row.created_at),
            }
        )

    items.sort(key=lambda x: x["created_at"] or "")
    if len(items) > limit:
        items = items[-limit:]
    return items


async def user_memories(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    result = await session.scalars(
        select(Memory)
        .where(Memory.user_id == user_id)
        .order_by(Memory.importance.desc(), Memory.created_at.desc())
    )
    return [
        {
            "id": m.id,
            "type": m.type,
            "importance": m.importance,
            "description": m.description,
            "happened_at": m.happened_at.isoformat() if m.happened_at else None,
            "is_active": m.is_active,
            "created_at": _dt(m.created_at),
        }
        for m in result
    ]


async def user_people(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    result = await session.scalars(
        select(RelationshipPerson).where(RelationshipPerson.user_id == user_id)
    )
    return [
        {
            "id": p.id,
            "display_name": p.display_name,
            "relationship_type": p.relationship_type,
            "sentiment": p.sentiment,
            "importance": p.importance,
            "notes": p.notes,
            "last_mentioned_at": _dt(p.last_mentioned_at),
        }
        for p in result
    ]


async def user_readings(session: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    """Leia product readings from ProductUsage (not legacy TarotReading)."""
    result = await session.scalars(
        select(ProductUsage)
        .where(
            ProductUsage.user_id == user_id,
            ProductUsage.content_preview.isnot(None),
            ProductUsage.content_preview != "",
        )
        .order_by(ProductUsage.created_at.desc())
        .limit(50)
    )
    out: list[dict[str, Any]] = []
    for row in result:
        item = _product_usage_dict(row)
        item["reading_type"] = item["product_title"]
        item["question"] = item["level_label"]
        item["interpretation"] = item["content_preview"]
        item["cards"] = []
        out.append(item)
    return out


_FEATURE_LABELS = {
    "chat": "Чат",
    "tarot_reading": "Расклад",
    "vision_aura": "Аура",
    "vision_palm": "Ладонь",
    "vision_custom": "Фото",
}

_BILLING_MODE_LABELS = {
    "free": "Бесплатно",
    "balance": "Баланс",
    "unlimited": "Безлимит",
}


async def user_billing(session: AsyncSession, user_id: str) -> dict[str, Any]:
    from app.services.billing.tokens import display_provider_cost_rub, display_provider_cost_usd

    payments = await session.scalars(
        select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc())
    )
    topups = await session.scalars(
        select(BalanceTransaction)
        .where(
            BalanceTransaction.user_id == user_id,
            BalanceTransaction.reason.like("admin_topup%"),
        )
        .order_by(BalanceTransaction.created_at.desc())
        .limit(50)
    )
    usage = await session.scalars(
        select(UsageRecord)
        .where(UsageRecord.user_id == user_id)
        .order_by(UsageRecord.created_at.desc())
        .limit(200)
    )

    payment_rows = [
        {
            "id": p.id,
            "purpose": p.purpose,
            "status": p.status,
            "amount_rub": _dec(p.amount_rub),
            "created_at": _dt(p.created_at),
        }
        for p in payments
    ]
    for topup in topups:
        payment_rows.append(
            {
                "id": topup.id,
                "purpose": "Пополнение (админ)",
                "status": "completed",
                "amount_rub": _dec(topup.amount_rub),
                "created_at": _dt(topup.created_at),
            }
        )
    payment_rows.sort(key=lambda row: row["created_at"] or "", reverse=True)

    usage_rows: list[dict[str, Any]] = []
    for u in usage:
        meta = u.meta or {}
        with_infographic = bool(meta.get("with_infographic"))
        feature_label = _FEATURE_LABELS.get(u.feature, u.feature)
        if with_infographic:
            feature_label = f"{feature_label} + инфографика"

        image_cost_raw = meta.get("image_provider_cost_usd")
        image_cost_usd = Decimal(str(image_cost_raw)) if image_cost_raw else Decimal("0")
        image_charged_raw = meta.get("image_charged_rub")

        usage_rows.append(
            {
                "id": u.id,
                "feature": u.feature,
                "feature_label": feature_label,
                "billing_mode": meta.get("billing_mode", "free"),
                "billing_mode_label": _BILLING_MODE_LABELS.get(
                    meta.get("billing_mode", "free"),
                    meta.get("billing_mode", "free"),
                ),
                "model": u.model,
                "input_units": u.input_units,
                "output_units": u.output_units,
                "total_tokens": u.input_units + u.output_units,
                "provider_cost_usd": _dec_usd(display_provider_cost_usd(u.provider_cost_usd)),
                "provider_cost_rub": _dec(display_provider_cost_rub(u.provider_cost_usd)),
                "kie_credits": meta.get("kie_credits"),
                "charged_rub": _dec(u.charged_rub),
                "with_infographic": with_infographic,
                "image_model": meta.get("image_model"),
                "image_provider_cost_usd": _dec_usd(display_provider_cost_usd(image_cost_usd))
                if with_infographic
                else None,
                "image_provider_cost_rub": _dec(display_provider_cost_rub(image_cost_usd))
                if with_infographic
                else None,
                "image_charged_rub": _dec(Decimal(str(image_charged_raw)))
                if image_charged_raw is not None
                else None,
                "chat_charged_rub": _dec(Decimal(str(meta["chat_charged_rub"])))
                if meta.get("chat_charged_rub") is not None
                else None,
                "source_image_url": meta.get("source_image_url"),
                "infographic_urls": meta.get("infographic_urls") or [],
                "created_at": _dt(u.created_at),
            }
        )

    return {
        "payments": payment_rows,
        "usage": usage_rows,
    }


async def bot_logs(session: AsyncSession, limit: int = 200) -> list[dict[str, Any]]:
    events = await session.scalars(
        select(AnalyticsEvent).order_by(AnalyticsEvent.created_at.desc()).limit(limit)
    )
    notif = await session.scalars(
        select(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit)
    )
    items = [
        {
            "kind": "event",
            "event_name": e.event_name,
            "user_id": e.user_id,
            "payload": e.payload,
            "created_at": _dt(e.created_at),
        }
        for e in events
    ]
    items.extend(
        {
            "kind": "notification",
            "event_name": n.status,
            "user_id": n.user_id,
            "payload": {"message": n.message},
            "created_at": _dt(n.created_at),
        }
        for n in notif
    )
    items.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return items[:limit]


async def request_logs(session: AsyncSession, limit: int = 200) -> list[dict[str, Any]]:
    from app.services.billing.tokens import display_provider_cost_usd

    usage = await session.scalars(
        select(UsageRecord).order_by(UsageRecord.created_at.desc()).limit(limit)
    )
    return [
        {
            "id": u.id,
            "user_id": u.user_id,
            "feature": u.feature,
            "provider": u.provider,
            "model": u.model,
            "input_units": u.input_units,
            "output_units": u.output_units,
            "provider_cost_usd": _dec_usd(display_provider_cost_usd(u.provider_cost_usd)),
            "charged_rub": _dec(u.charged_rub),
            "meta": u.meta,
            "created_at": _dt(u.created_at),
        }
        for u in usage
    ]


_PAYMENT_PURPOSE_LABELS = {
    "topup": "Пополнение баланса",
    "subscription_plus": "Подписка Plus (legacy)",
    "subscription_premium": "Подписка Premium (legacy)",
    "subscription_love_plus": "ЛЮБОВЬ+ — подписка на месяц",
    "subscription_vip": "VIP-пакет — подписка на месяц",
    "combo_happy_woman": "Комбо «Счастливая женщина»",
    "product_tarot_spread_full": "Расклад Таро — полная расшифровка",
    "product_love_full": "Любовь — полная расшифровка",
    "product_chat_full": "Переписка — полная расшифровка",
    "product_wealth_full": "Денежный код — полная расшифровка",
    "product_negative_full": "Диагностика негатива — полная",
    "product_forecast_full": "Матрица судьбы — полная",
    "product_question_full": "Ответ на вопрос — полная",
}

_ENTITLEMENT_KIND_LABELS = {
    "vip": "VIP-пакет",
    "love_plus": "ЛЮБОВЬ+",
    "combo_love": "Комбо: Любовь",
    "combo_wealth": "Комбо: Деньги",
    "combo_forecast": "Комбо: Прогноз",
}

_PAYMENT_STATUS_LABELS = {
    "pending": "Ожидает",
    "completed": "Проведён",
    "rejected": "Отклонён",
}


def _payment_row(payment: Payment, user: User) -> dict[str, Any]:
    payload = dict(payment.payload or {})
    return {
        "id": payment.id,
        "user_id": payment.user_id,
        "user_name": user.first_name or user.username,
        "telegram_id": user.telegram_id,
        "provider": payment.provider,
        "provider_payment_id": payment.provider_payment_id,
        "purpose": payment.purpose,
        "purpose_label": _PAYMENT_PURPOSE_LABELS.get(payment.purpose, payment.purpose),
        "status": payment.status,
        "status_label": _PAYMENT_STATUS_LABELS.get(payment.status, payment.status),
        "amount_rub": _dec(payment.amount_rub),
        "admin_comment": payload.get("admin_comment"),
        "created_at": _dt(payment.created_at),
        "updated_at": _dt(payment.updated_at) if hasattr(payment, "updated_at") else None,
    }


async def list_payments(session: AsyncSession, limit: int = 100) -> list[dict[str, Any]]:
    result = await session.execute(
        select(Payment, User)
        .join(User, User.id == Payment.user_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    return [_payment_row(payment, user) for payment, user in result.all()]


async def payment_detail(session: AsyncSession, payment_id: str) -> dict[str, Any] | None:
    row = await session.execute(
        select(Payment, User)
        .join(User, User.id == Payment.user_id)
        .where(Payment.id == payment_id)
    )
    pair = row.first()
    if pair is None:
        return None
    payment, user = pair
    base = _payment_row(payment, user)
    payload = dict(payment.payload or {})
    # Do not dump huge generated reading text twice; show short preview.
    generated = str(payload.get("generated_text") or "")
    safe_payload = {
        k: v
        for k, v in payload.items()
        if k not in {"generated_text"}
    }
    if generated:
        safe_payload["generated_text_preview"] = generated[:800]
        safe_payload["generated_text_len"] = len(generated)

    usages = await session.scalars(
        select(ProductUsage)
        .where(ProductUsage.payment_id == payment.id)
        .order_by(ProductUsage.created_at.desc())
    )
    return {
        **base,
        "payload": safe_payload,
        "product_usages": [_product_usage_dict(u) for u in usages],
        "referral_discount_percent": payload.get("referral_discount_percent"),
        "original_amount_rub": payload.get("original_amount_rub"),
        "payment_url": payload.get("payment_url"),
        "inv_id": payload.get("inv_id") or payload.get("robokassa_inv_id"),
        "robokassa_out_sum": payload.get("robokassa_out_sum"),
    }


async def list_withdrawals(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(
        select(ReferralWithdrawalRequest, User)
        .join(User, User.id == ReferralWithdrawalRequest.user_id)
        .order_by(ReferralWithdrawalRequest.created_at.desc())
    )
    return [
        {
            "id": req.id,
            "user_id": req.user_id,
            "user_name": user.first_name or user.username,
            "telegram_id": user.telegram_id,
            "amount_rub": _dec(req.amount_rub),
            "status": req.status,
            "payout_details": req.payout_details,
            "admin_comment": req.admin_comment,
            "created_at": _dt(req.created_at),
        }
        for req, user in result.all()
    ]


async def list_referrals(session: AsyncSession) -> list[dict[str, Any]]:
    from app.services.referrals.discount import REFERRED_DISCOUNT_PERCENT

    referrer = (
        select(
            Referral,
            User.first_name,
            User.username,
            User.telegram_id,
            User.referral_reward_percent,
        )
        .join(User, User.id == Referral.referrer_user_id)
    )
    result = await session.execute(referrer)
    rows = result.all()
    referred_ids = [ref.referred_user_id for ref, *_ in rows if ref.referred_user_id]
    referred_map: dict[str, User] = {}
    if referred_ids:
        referred_users = await session.scalars(select(User).where(User.id.in_(referred_ids)))
        referred_map = {u.id: u for u in referred_users}

    out: list[dict[str, Any]] = []
    for ref, name, username, telegram_id, partner_percent in rows:
        referred = referred_map.get(ref.referred_user_id or "")
        out.append(
            {
                "id": ref.id,
                "referrer_user_id": ref.referrer_user_id,
                "referrer_name": name or username,
                "referrer_telegram_id": telegram_id,
                "partner_reward_percent": partner_percent,
                "referred_user_id": ref.referred_user_id,
                "referred_name": (
                    (referred.first_name or referred.username) if referred else None
                ),
                "referred_telegram_id": referred.telegram_id if referred else None,
                "reward_percent": ref.reward_percent,
                "buyer_discount_percent": REFERRED_DISCOUNT_PERCENT,
                "accrued_rub": _dec(ref.accrued_rub),
                "created_at": _dt(ref.created_at),
            }
        )
    return out


async def list_tarot_cards(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.scalars(select(TarotCard).order_by(TarotCard.number))
    return [
        {
            "id": c.id,
            "slug": c.slug,
            "name": c.name,
            "number": c.number,
            "arcana": c.arcana,
            "image_path": c.image_path,
            "description": c.description,
        }
        for c in result
    ]
