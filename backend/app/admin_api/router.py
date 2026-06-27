from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_api import service as admin_service
from app.admin_api.auth import get_current_admin
from app.core.config import get_settings
from app.database.models import Payment, ReferralWithdrawalRequest, TarotCard, User
from app.database.session import get_session
from app.services.billing.platega_client import fetch_balances
from app.services.billing.service import BillingService
from app.services.landing import analytics as landing_analytics
from app.services.telegram_notify import notify_owner, notify_telegram_message

router = APIRouter(tags=["admin"], dependencies=[Depends(get_current_admin)])


@router.get("/dashboard")
async def dashboard(session: AsyncSession = Depends(get_session)) -> dict:
    stats = await admin_service.dashboard_stats(session)
    balances, error = await fetch_balances()
    stats["platega_balances"] = balances
    if error:
        stats["platega_balances_error"] = error
    return stats


@router.get("/platega/balances")
async def platega_balances() -> dict:
    balances, error = await fetch_balances()
    return {"balances": balances, "error": error}


@router.get("/stats/signups")
async def signups_chart(session: AsyncSession = Depends(get_session), days: int = 30) -> list[dict]:
    return await admin_service.signups_chart(session, days=days)


@router.get("/stats/landing")
async def landing_stats(
    session: AsyncSession = Depends(get_session),
    days: int = Query(default=30, ge=1, le=365),
) -> dict:
    return await landing_analytics.landing_stats(session, days=days)


@router.get("/stats/tokens")
async def token_stats(
    session: AsyncSession = Depends(get_session),
    days: int = Query(default=30, ge=1, le=365),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> dict:
    return await admin_service.token_stats(session, days=days, date_from=date_from, date_to=date_to)


@router.get("/users")
async def users(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await admin_service.list_users(session)


@router.get("/users/{user_id}")
async def user_detail(user_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    data = await admin_service.user_detail(session, user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="User not found")
    return data


@router.get("/users/{user_id}/messages")
async def user_messages(user_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await admin_service.user_messages(session, user_id)


@router.get("/users/{user_id}/memories")
async def user_memories(user_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await admin_service.user_memories(session, user_id)


@router.get("/users/{user_id}/people")
async def user_people(user_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await admin_service.user_people(session, user_id)


@router.get("/users/{user_id}/readings")
async def user_readings(user_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await admin_service.user_readings(session, user_id)


@router.get("/users/{user_id}/billing")
async def user_billing(user_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    return await admin_service.user_billing(session, user_id)


class AdminTopupRequest(BaseModel):
    amount_rub: Decimal = Field(gt=0)
    comment: str = ""


@router.post("/users/{user_id}/balance/topup")
async def admin_topup_balance(
    user_id: str,
    body: AdminTopupRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        result = await BillingService().admin_topup_balance(
            session,
            user,
            body.amount_rub,
            comment=body.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return {
        "user_id": user.id,
        "amount_rub": str(result["amount_rub"]),
        "balance_rub": str(result["balance_rub"]),
    }


@router.get("/logs/bot")
async def bot_logs(session: AsyncSession = Depends(get_session), limit: int = 200) -> list[dict]:
    return await admin_service.bot_logs(session, limit=limit)


@router.get("/logs/requests")
async def request_logs(session: AsyncSession = Depends(get_session), limit: int = 200) -> list[dict]:
    return await admin_service.request_logs(session, limit=limit)


@router.get("/billing/payments")
async def payments(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await admin_service.list_payments(session)


@router.patch("/billing/payments/{payment_id}")
async def update_payment(
    payment_id: str,
    status: str = Query(...),
    admin_comment: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    payment = await session.scalar(select(Payment).where(Payment.id == payment_id))
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    billing = BillingService()
    try:
        if status == "completed":
            result = await billing.complete_payment(
                session,
                payment,
                admin_comment=admin_comment or "",
            )
        elif status == "rejected":
            result = await billing.reject_payment(
                session,
                payment,
                admin_comment=admin_comment or "",
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported status")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await session.commit()
    notify = result.get("telegram_notify")
    if isinstance(notify, dict):
        billing = BillingService()
        keyboard = await billing.reply_main_menu_markup(int(notify["telegram_id"]))
        notify_telegram_message(
            int(notify["telegram_id"]),
            str(notify["text"]),
            reply_markup=keyboard,
        )
    owner_text = result.get("owner_notify")
    if isinstance(owner_text, str):
        await notify_owner(owner_text)
    return result


@router.delete("/billing/payments/{payment_id}")
async def delete_payment(
    payment_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    payment = await session.scalar(select(Payment).where(Payment.id == payment_id))
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    try:
        await BillingService().delete_payment(session, payment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await session.commit()
    return {"id": payment_id, "deleted": True}


@router.get("/referrals")
async def referrals(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await admin_service.list_referrals(session)


@router.get("/referrals/withdrawals")
async def withdrawals(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await admin_service.list_withdrawals(session)


@router.patch("/referrals/withdrawals/{request_id}")
async def update_withdrawal(
    request_id: str,
    status: str = Query(...),
    admin_comment: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    req = await session.scalar(
        select(ReferralWithdrawalRequest).where(ReferralWithdrawalRequest.id == request_id)
    )
    if req is None:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")
    req.status = status
    if admin_comment is not None:
        req.admin_comment = admin_comment
    await session.commit()
    return {"id": req.id, "status": req.status}


@router.get("/tarot-cards")
async def tarot_cards(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await admin_service.list_tarot_cards(session)


@router.post("/tarot-cards/upload")
async def upload_tarot_card(
    slug: str = Form(...),
    name: str = Form(...),
    number: int = Form(...),
    arcana: str = Form("major"),
    description: str = Form(""),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    settings = get_settings()
    cards_dir = Path(settings.tarot_cards_dir)
    cards_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "card.png").suffix or ".png"
    filename = f"{number}_{slug}{ext}"
    dest = cards_dir / filename
    content = await file.read()
    dest.write_bytes(content)

    image_path = str(cards_dir / filename)
    card = await session.scalar(select(TarotCard).where(TarotCard.slug == slug))
    if card is None:
        card = TarotCard(
            slug=slug,
            name=name,
            number=number,
            arcana=arcana,
            description=description,
            image_path=image_path,
        )
        session.add(card)
    else:
        card.name = name
        card.number = number
        card.arcana = arcana
        card.description = description
        card.image_path = image_path
    await session.commit()
    await session.refresh(card)
    return {"id": card.id, "slug": card.slug, "image_path": card.image_path}
