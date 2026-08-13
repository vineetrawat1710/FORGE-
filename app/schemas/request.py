from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.request import AuthorizationType, BodyType, HttpMethod


def _trim(value: str | None) -> str | None:
    if isinstance(value, str):
        return value.strip()
    return value


class RequestHeaderBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1, max_length=2048)
    description: str | None = Field(default=None, max_length=255)
    enabled: bool = True

    @field_validator("key", "value", "description", mode="before")
    @classmethod
    def trim_strings(cls, value):
        return _trim(value)

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if not value or any(ch.isspace() for ch in value):
            raise ValueError("Header names cannot contain whitespace.")
        return value


class RequestQueryParameterBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=0, max_length=2048)
    description: str | None = Field(default=None, max_length=255)
    enabled: bool = True

    @field_validator("key", "value", "description", mode="before")
    @classmethod
    def trim_strings(cls, value):
        return _trim(value)

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if not value:
            raise ValueError("Query parameter name cannot be empty.")
        return value


class RequestAuthorizationBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AuthorizationType = AuthorizationType.NONE
    token: str | None = Field(default=None, max_length=4096)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=255)
    api_key_name: str | None = Field(default=None, max_length=255)
    api_key_value: str | None = Field(default=None, max_length=4096)
    api_key_in: str | None = Field(default=None, max_length=20)

    @field_validator("token", "username", "password", "api_key_name", "api_key_value", "api_key_in", mode="before")
    @classmethod
    def trim_optional_strings(cls, value):
        return _trim(value)

    @field_validator("api_key_in")
    @classmethod
    def validate_api_key_in(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in {"header", "query"}:
            raise ValueError("API key location must be header or query.")
        return value


class RequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    method: HttpMethod
    url: str = Field(..., min_length=1, max_length=2048)
    body: str | None = Field(default=None)
    body_type: BodyType = BodyType.NONE
    timeout: int = Field(default=30, ge=1, le=300)
    follow_redirects: bool = True
    verify_ssl: bool = True
    is_favorite: bool = False
    collection_id: UUID | None = None
    environment_id: UUID | None = None
    headers: list[RequestHeaderBase] = Field(default_factory=list)
    query_parameters: list[RequestQueryParameterBase] = Field(default_factory=list)
    authorization: RequestAuthorizationBase = Field(default_factory=RequestAuthorizationBase)

    @field_validator("name", "description", "body", mode="before")
    @classmethod
    def trim_strings(cls, value):
        return _trim(value)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if "{{" in value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("URL must be a valid http or https URL.")
        return value

    @field_validator("body")
    @classmethod
    def validate_body_and_type(cls, value: str | None, info):
        body_type = info.data.get("body_type")
        if body_type == BodyType.NONE and value not in (None, ""):
            raise ValueError("Body must be empty when body_type is none.")
        return value


class RequestCreate(RequestBase):
    pass


class RequestUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    method: HttpMethod | None = None
    url: str | None = Field(default=None, max_length=2048)
    body: str | None = None
    body_type: BodyType | None = None
    timeout: int | None = Field(default=None, ge=1, le=300)
    follow_redirects: bool | None = None
    verify_ssl: bool | None = None
    is_favorite: bool | None = None
    collection_id: UUID | None = None
    environment_id: UUID | None = None
    headers: list[RequestHeaderBase] | None = None
    query_parameters: list[RequestQueryParameterBase] | None = None
    authorization: RequestAuthorizationBase | None = None

    @field_validator("name", "description", "body", mode="before")
    @classmethod
    def trim_strings(cls, value):
        return _trim(value)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None or "{{" in value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("URL must be a valid http or https URL.")
        return value


class RequestHeaderResponse(RequestHeaderBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    request_id: UUID


class RequestQueryParameterResponse(RequestQueryParameterBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    request_id: UUID


class RequestAuthorizationResponse(RequestAuthorizationBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    request_id: UUID


class RequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    user_id: UUID
    collection_id: UUID | None
    environment_id: UUID | None
    name: str
    description: str | None
    method: HttpMethod
    url: str
    body: str | None
    body_type: BodyType
    timeout: int
    follow_redirects: bool
    verify_ssl: bool
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
    headers: list[RequestHeaderResponse] = Field(default_factory=list)
    query_parameters: list[RequestQueryParameterResponse] = Field(default_factory=list)
    authorization: RequestAuthorizationResponse | None = None


class ConsoleLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    level: str  # INFO, REQUEST, SUCCESS, WARNING, ERROR
    message: str
    details: str | None = None


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status_code: int | None
    reason_phrase: str | None
    headers: dict[str, str]
    body: str | None
    response_size: int | None
    duration_ms: float
    content_type: str | None
    cookies: dict[str, str]
    redirect_count: int
    timestamp: datetime
    error: str | None = None
    console_logs: list[ConsoleLog] = Field(default_factory=list)


class ExecutionHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    request_id: UUID | None
    duration_ms: float
    status_code: int | None
    execution_status: str
    executed_at: datetime
    error: str | None


class ExecutionHistoryPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExecutionHistoryResponse]
    total: int
    limit: int
    offset: int


class GlobalHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    request_id: UUID | None = None
    method: str
    url: str
    status_code: int | None = None
    duration_ms: float
    response_size: int | None = None
    environment_id: UUID | None = None
    executed_at: datetime
    execution_status: str


class GlobalHistoryDetailResponse(GlobalHistoryResponse):
    request_snapshot: dict[str, Any]
    response_snapshot: dict[str, Any] | None = None


class GlobalHistoryPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[GlobalHistoryResponse]
    total: int
    limit: int
    offset: int
