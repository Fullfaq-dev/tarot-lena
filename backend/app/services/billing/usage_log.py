"""Record KIE usage for Leia product/chat flows (admin token stats)."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select

from app.core.config import get_settings
from app.database.models import UsageRecord, User
from app.database.session import AsyncSessionLocal
from app.services.billing.tokens import (
    estimate_tokens,
    provider_cost_credits,
    provider_cost_usd,
    total_tokens,
)

logger = logging.getLogger(__name__)


async def record_kie_usage(
    user_id: str,
    *,
    feature: str,
    question: str = "",
    answer: str = "",
    api_usage: dict | None = None,
    extra_meta: dict | None = None,
) -> None:
    """Persist usage without charging the user (Leia fixed-price products)."""
    if not user_id:
        return
    try:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.id == user_id))
            if user is None:
                return

            q_tokens = estimate_tokens(question)
            a_tokens = estimate_tokens(answer)
            if api_usage and (api_usage.get("input_tokens") or api_usage.get("output_tokens")):
                input_tokens = int(api_usage.get("input_tokens") or 0)
                output_tokens = int(api_usage.get("output_tokens") or a_tokens)
                cost_source = "kie_api"
            else:
                input_tokens = q_tokens
                output_tokens = a_tokens
                cost_source = "estimated"
            if input_tokens <= 0 and output_tokens <= 0:
                return

            cost_credits = provider_cost_credits(input_tokens, output_tokens)
            cost_usd = provider_cost_usd(input_tokens, output_tokens)
            settings = get_settings()
            model = settings.kie_chat_model or "gpt-5-6-luna"
            provider = "kie"
            if api_usage:
                raw_model = api_usage.get("model")
                if isinstance(raw_model, str) and raw_model.strip():
                    model = raw_model.strip()
                raw_provider = api_usage.get("provider")
                if isinstance(raw_provider, str) and raw_provider.strip():
                    provider = raw_provider.strip()
            session.add(
                UsageRecord(
                    user_id=user.id,
                    feature=feature,
                    provider=provider,
                    model=model,
                    input_units=input_tokens,
                    output_units=output_tokens,
                    provider_cost_usd=cost_usd,
                    charged_rub=Decimal("0"),
                    meta={
                        "question_tokens": q_tokens,
                        "answer_tokens": a_tokens,
                        "question_preview": (question or "")[:200],
                        "billing_mode": "product",
                        "cost_source": cost_source,
                        "total_tokens": total_tokens(input_tokens, output_tokens),
                        "kie_credits": str(cost_credits),
                        **(extra_meta or {}),
                    },
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to record KIE usage user_id=%s feature=%s", user_id, feature)
