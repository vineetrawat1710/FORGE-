from app.ai.providers.base import AIProvider
from app.ai.providers.local_provider import LocalAIProvider
from app.ai.providers.groq_provider import GroqProvider
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.anthropic_provider import AnthropicProvider
from app.ai.providers.gemini_provider import GeminiProvider


def build_provider(name: str, model: str | None = None) -> AIProvider:
    provider_name = (name or "local").strip().lower()
    if provider_name == "groq":
        return GroqProvider(model=model)
    if provider_name == "openai":
        return OpenAIProvider(model=model or "gpt-4.1-mini")
    if provider_name == "anthropic":
        return AnthropicProvider(model=model or "claude-sonnet-4")
    if provider_name == "gemini":
        return GeminiProvider(model=model or "gemini-2.0-flash")
    return LocalAIProvider()
