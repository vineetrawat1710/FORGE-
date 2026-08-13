from __future__ import annotations


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError("GeminiProvider is a scaffold. Configure a Gemini client to enable it.")

