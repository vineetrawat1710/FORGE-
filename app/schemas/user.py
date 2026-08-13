import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _trim_string(value: str | None) -> str | None:
    if isinstance(value, str):
        return value.strip()
    return value


def _validate_username(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", value):
        raise ValueError("Username must be 3-20 characters long and contain only letters, numbers, and underscores.")
    return value


def _validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must contain at least one special character.")
    return value


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="The user's email address.")
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="A unique username made of letters, numbers, and underscores.",
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Password must be at least 8 characters and include uppercase, lowercase, a number, and a special character.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def trim_email(cls, value: str) -> str:
        return _trim_string(value)

    @field_validator("username", mode="before")
    @classmethod
    def trim_username(cls, value: str) -> str:
        return _trim_string(value)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return _validate_username(value)

    @field_validator("password", mode="before")
    @classmethod
    def trim_password(cls, value: str) -> str:
        return _trim_string(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="The user's email address for login.")
    password: str = Field(
        ...,
        min_length=8,
        description="The user's password. Leading and trailing spaces are ignored.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def trim_email(cls, value: str) -> str:
        return _trim_string(value)

    @field_validator("password", mode="before")
    @classmethod
    def trim_password(cls, value: str) -> str:
        return _trim_string(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID = Field(..., description="Unique user identifier.")
    email: EmailStr = Field(..., description="User email address.")
    username: str = Field(..., description="Public username.")
    is_active: bool = Field(..., description="Whether the user account is active.")
    created_at: datetime = Field(..., description="Account creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class Token(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(..., description="JWT access token used to authenticate requests.")
    refresh_token: str = Field(..., description="JWT refresh token used to obtain a new access token.")
    token_type: str = Field(default="bearer", description="Type of authentication token.")


class TokenPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub: str = Field(..., description="Subject claim identifying the user.")
    exp: datetime = Field(..., description="Token expiration time in UTC.")


RegisterRequest = UserCreate
LoginRequest = UserLogin
TokenResponse = Token
RefreshTokenRequest = TokenPayload
