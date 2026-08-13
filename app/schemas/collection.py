from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _trim(value: str | None) -> str | None:
    if isinstance(value, str):
        return value.strip()
    return value


class CollectionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    is_favorite: bool = False
    tags: list[str] = Field(default_factory=list)

    @field_validator("name", "description", mode="before")
    @classmethod
    def trim_strings(cls, value):
        return _trim(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        cleaned = []
        for tag in value:
            if not tag or not isinstance(tag, str):
                continue
            tag = tag.strip()
            if tag:
                cleaned.append(tag)
        return list(dict.fromkeys(cleaned))


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    is_favorite: bool | None = None
    tags: list[str] | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def trim_strings(cls, value):
        return _trim(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned = []
        for tag in value:
            if not tag or not isinstance(tag, str):
                continue
            tag = tag.strip()
            if tag:
                cleaned.append(tag)
        return list(dict.fromkeys(cleaned))


class CollectionTagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    collection_id: UUID
    name: str


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    user_id: UUID
    name: str
    description: str | None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
    tags: list[CollectionTagResponse] = Field(default_factory=list)
