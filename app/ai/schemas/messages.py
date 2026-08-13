from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AIMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)

