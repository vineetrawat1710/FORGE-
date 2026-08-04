from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.user import UserResponse
from app.services.user_service import UserService

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> UserResponse:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    service = UserService(db)
    return service.get_profile(UUID(user_id))
