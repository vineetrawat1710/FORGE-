from __future__ import annotations

from enum import StrEnum
from dataclasses import dataclass


class AITask(StrEnum):
    REASONING = "reasoning"
    LARGE_CONTEXT = "large_context"
    FAST = "fast"


@dataclass(frozen=True)
class Classification:
    task: AITask
    confidence: float
    reason: str


class TaskClassifier:
    """Selects a model family from the user's task, not from the UI surface."""

    def classify(self, message: str, task: str | None = None, input_size: int = 0, is_openapi: bool = False) -> Classification:
        value = f"{task or ''} {message}".lower()
        if is_openapi or any(term in value for term in ("openapi", "swagger", "postman collection", "large json", "schema", "long response", "document")) or input_size > 100_000:
            return Classification(AITask.LARGE_CONTEXT, 0.96 if is_openapi or input_size > 100_000 else 0.86, "large structured input")
        if any(term in value for term in ("summarize", "summary", "rewrite", "shorten", "quick")):
            return Classification(AITask.FAST, 0.9, "lightweight transformation")
        return Classification(AITask.REASONING, 0.84, "reasoning or tool use")
