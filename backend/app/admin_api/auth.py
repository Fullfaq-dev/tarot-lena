from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.database.models import AdminUser
from app.database.session import AsyncSessionLocal, get_session

_bearer = HTTPBearer(auto_error=False)


def decode_access_token(token: str) -> str:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    subject = payload.get("sub")
    if not subject:
        raise JWTError("Missing subject")
    return str(subject)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> AdminUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        admin_id = decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    admin = await session.scalar(
        select(AdminUser).where(AdminUser.id == admin_id, AdminUser.is_active.is_(True))
    )
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return admin


async def ensure_bootstrap_admin() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(AdminUser))
        if int(count or 0) > 0:
            return
        session.add(
            AdminUser(
                email=settings.admin_bootstrap_email.strip().lower(),
                password_hash=hash_password(settings.admin_bootstrap_password),
                role="owner",
            )
        )
        await session.commit()
