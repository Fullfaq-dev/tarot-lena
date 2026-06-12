from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.database.models import AdminUser
from app.database.session import get_session

router = APIRouter(tags=["admin-auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> LoginResponse:
    email = body.email.strip().lower()
    admin = await session.scalar(
        select(AdminUser).where(AdminUser.email == email, AdminUser.is_active.is_(True))
    )
    if admin is None or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    return LoginResponse(
        access_token=create_access_token(admin.id),
        email=admin.email,
    )
