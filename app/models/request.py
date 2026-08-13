import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.collection import Collection


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class BodyType(str, Enum):
    NONE = "none"
    JSON = "json"
    TEXT = "text"
    FORM = "form"
    MULTIPART = "multipart"
    XML = "xml"


class AuthorizationType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api_key"


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    collection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("collections.id", ondelete="SET NULL"), index=True, nullable=True)
    environment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("environments.id", ondelete="SET NULL"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_type: Mapped[str] = mapped_column(String(20), nullable=False, default=BodyType.NONE.value)
    timeout: Mapped[int] = mapped_column(nullable=False, default=30)
    follow_redirects: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verify_ssl: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    headers = relationship("RequestHeader", cascade="all, delete-orphan", passive_deletes=True)
    query_parameters = relationship("RequestQueryParameter", cascade="all, delete-orphan", passive_deletes=True)
    authorization = relationship("RequestAuthorization", uselist=False, cascade="all, delete-orphan", passive_deletes=True)


class RequestHeader(Base):
    __tablename__ = "request_headers"
    __table_args__ = (UniqueConstraint("request_id", "key", name="uq_request_headers_request_id_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RequestQueryParameter(Base):
    __tablename__ = "request_query_parameters"
    __table_args__ = (UniqueConstraint("request_id", "key", name="uq_request_query_parameters_request_id_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RequestAuthorization(Base):
    __tablename__ = "request_authorizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default=AuthorizationType.NONE.value)
    token: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_key_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_key_value: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    api_key_in: Mapped[str | None] = mapped_column(String(20), nullable=True)


class RequestExecutionHistory(Base):
    __tablename__ = "request_execution_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("requests.id", ondelete="SET NULL"), index=True, nullable=True)
    request_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    response_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float] = mapped_column(nullable=False)
    status_code: Mapped[int | None] = mapped_column(nullable=True)
    execution_status: Mapped[str] = mapped_column(String(30), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
