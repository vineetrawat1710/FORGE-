from __future__ import annotations


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4"):
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError("AnthropicProvider is a scaffold. Configure an Anthropic client to enable it.")

