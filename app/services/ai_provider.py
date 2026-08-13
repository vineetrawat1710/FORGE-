from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class AIMessage:
    role: str
    content: str


class AIProvider(Protocol):
    def generate(self, messages: list[AIMessage]) -> str: ...


class LocalAIProvider:
    def generate(self, messages: list[AIMessage]) -> str:
        return messages[-1].content if messages else ""
