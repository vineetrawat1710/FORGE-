from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EnvironmentBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    variables: dict[str, dict[str, object]] = Field(default_factory=dict)

    @field_validator("name", "description", mode="before")
    @classmethod
    def trim_strings(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value


class EnvironmentCreate(EnvironmentBase):
    is_active: bool = False


class EnvironmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    variables: dict[str, dict[str, object]] | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def trim_strings(cls, value):
        if isinstance(value, str):
            value = value.strip()
        return value


class EnvironmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    user_id: UUID
    name: str
    description: str | None
    variables: dict[str, dict[str, object]]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EnvironmentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
