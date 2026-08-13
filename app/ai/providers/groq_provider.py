from __future__ import annotations

import json

import httpx

from app.core.config import get_settings


class GroqProvider:
    name = "groq"

    def __init__(self, model: str | None = None):
        settings = get_settings()
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required for GroqProvider.")
        self.api_key = settings.groq_api_key
        self.base_url = settings.groq_base_url.rstrip("/")
        self.model = model or settings.ai_model
        self.temperature = settings.ai_temperature
        self.max_tokens = settings.ai_max_tokens
        self.timeout_seconds = settings.ai_timeout_seconds

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.post("/chat/completions", headers=headers, content=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return str(message.get("content", "")).strip()
