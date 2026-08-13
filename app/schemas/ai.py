from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.collection import CollectionResponse
from app.schemas.environment import EnvironmentResponse
from app.schemas.import_export import ExportResponse
from app.schemas.request import ExecutionResponse, RequestResponse


class AIChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1)
    context_request_id: str | None = None
    context_collection_id: str | None = None
    context_environment_id: str | None = None
    task: str | None = None
    input_size: int = Field(default=0, ge=0)
    is_openapi: bool = False


class AIGenerateRequestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., min_length=1)


class AIExplainResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    response: ExecutionResponse | None = None


class AIGenerateCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: RequestResponse
    language: str = Field(..., min_length=2)


class AIDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: RequestResponse
    response: ExecutionResponse | None = None


class AISearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)


class AIToolResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    result: dict[str, object]


class AIChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str
    tools: list[AIToolResponse] = Field(default_factory=list)


class AIGenerateRequestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: dict[str, object]


class AISearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requests: list[RequestResponse] = Field(default_factory=list)
    collections: list[CollectionResponse] = Field(default_factory=list)
    environments: list[EnvironmentResponse] = Field(default_factory=list)
