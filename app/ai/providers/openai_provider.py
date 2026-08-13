from __future__ import annotations


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str = "gpt-4.1-mini"):
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError("OpenAIProvider is a scaffold. Configure an OpenAI client to enable it.")

