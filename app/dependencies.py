from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, InactiveUserError, InvalidTokenError
from app.core.security import decode_token
from app.schemas.user import UserResponse
from app.services.user_service import UserService

settings = get_settings()
security = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(security),
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        payload = decode_token(token, settings.secret_key, "access")
    except InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token.")

    service = UserService(db)
    user = service.get_user_by_id(UUID(user_id))
    if user is None:
        raise AuthenticationError("User not found.")
    if not user.is_active:
        raise InactiveUserError("User account is inactive.")

    return UserResponse.model_validate(user)
