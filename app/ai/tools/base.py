from __future__ import annotations

from typing import Protocol

from app.ai.context.context_builder import AIContext


class AITool(Protocol):
    name: str

    def run(self, context: AIContext, arguments: dict[str, object]) -> dict[str, object]: ...

