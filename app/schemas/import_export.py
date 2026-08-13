from pydantic import BaseModel, ConfigDict, Field


class RawImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., min_length=1)
    collection_name: str | None = Field(default=None, max_length=120)


class ImportSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str
    collections_created: int = 0
    requests_created: int = 0
    skipped_items: int = 0
    collection_id: str | None = None
    notes: list[str] = Field(default_factory=list)


class ExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: str
    filename: str
    content: str
