from __future__ import annotations

from app.ai.context.context_builder import AIContext
from app.ai.tools.base import AITool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, AITool] = {}

    def register(self, tool: AITool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> AITool:
        if name not in self._tools:
            raise KeyError(name)
        return self._tools[name]

    def list(self) -> list[str]:
        return sorted(self._tools)

