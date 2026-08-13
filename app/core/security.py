from datetime import datetime, timedelta, timezone
from typing import Any

from passlib.context import CryptContext
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.refresh_secret_key, algorithm=settings.algorithm)


def decode_token(token: str, secret_key: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired.") from exc
    except JWTError as exc:
        raise InvalidTokenError("Token is invalid.") from exc

    if payload.get("sub") is None or payload.get("type") != expected_type:
        raise InvalidTokenError("Token is invalid.")

    return payload
