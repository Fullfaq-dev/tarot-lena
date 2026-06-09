from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_minutes: int = 60 * 12) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    return jwt.encode({"sub": subject, "exp": expires_at}, settings.jwt_secret, algorithm="HS256")
