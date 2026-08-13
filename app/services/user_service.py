from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UsernameAlreadyExistsError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse

settings = get_settings()


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)

    def register(self, payload: UserCreate) -> UserResponse:
        existing_user = self.repository.get_by_email(str(payload.email))
        if existing_user is not None:
            raise UserAlreadyExistsError("User with this email already exists.")

        existing_username = self.repository.get_by_username(payload.username)
        if existing_username is not None:
            raise UsernameAlreadyExistsError("This username is already taken.")

        user = User(
            email=str(payload.email),
            username=payload.username,
            password_hash=hash_password(payload.password),
        )
        created_user = self.repository.create(user)
        return UserResponse.model_validate(created_user)

    def login(self, payload: UserLogin) -> Token:
        user = self.repository.get_by_email(str(payload.email))
        if user is None or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            raise InactiveUserError("User account is inactive.")

        return Token(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
            token_type="bearer",
        )

    def refresh(self, refresh_token: str) -> Token:
        payload = decode_token(refresh_token, settings.refresh_secret_key, "refresh")
        user_id = UUID(payload["sub"])
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found.")
        if not user.is_active:
            raise InactiveUserError("User account is inactive.")

        return Token(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
            token_type="bearer",
        )

    def get_profile(self, user_id: UUID) -> UserResponse:
        user = self.repository.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found.")
        return UserResponse.model_validate(user)

    def get_user_by_id(self, user_id: UUID) -> User | None:
        return self.repository.get_by_id(user_id)
