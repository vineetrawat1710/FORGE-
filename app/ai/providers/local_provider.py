from __future__ import annotations

from app.ai.providers.base import AIProvider


class LocalAIProvider:
    name = "local"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if "generate request" in user_prompt.lower():
            return "tool:generate_request"
        if "explain" in user_prompt.lower():
            return "tool:explain_response"
        return user_prompt.strip() or system_prompt.strip() or "ok"

