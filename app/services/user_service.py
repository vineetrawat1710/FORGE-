from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserResponse

settings = get_settings()


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)

    def register(self, payload: RegisterRequest) -> UserResponse:
        existing_user = self.repository.get_by_email(str(payload.email))
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists.",
            )

        existing_username = self.repository.get_by_username(payload.username)
        if existing_username is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists.",
            )

        user = User(
            email=str(payload.email),
            username=payload.username,
            password_hash=hash_password(payload.password),
        )
        created_user = self.repository.create(user)
        return UserResponse.model_validate(created_user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.repository.get_by_email(str(payload.email))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        token = self._create_access_token(user.id)
        return TokenResponse(access_token=token)

    def get_profile(self, user_id: UUID) -> UserResponse:
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return UserResponse.model_validate(user)

    def _create_access_token(self, user_id: UUID) -> str:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        expire_time = datetime.now(timezone.utc) + expires_delta
        token_payload = {"sub": str(user_id), "exp": expire_time}
        return jwt.encode(token_payload, settings.secret_key, algorithm=settings.algorithm)
