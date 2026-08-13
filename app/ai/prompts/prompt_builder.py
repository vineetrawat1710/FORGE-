from __future__ import annotations

from app.ai.context.context_builder import AIContext


class PromptBuilder:
    def system_prompt(self) -> str:
        return "You are API Studio AI. Use tools. Never guess hidden data. Never expose secrets."

    def tool_prompt(self) -> str:
        return "Choose one approved tool at a time and return structured output."

    def error_prompt(self) -> str:
        return "Explain the failure using the available response, status code, and headers."

    def code_prompt(self) -> str:
        return "Generate code for the selected request in the requested language."

    def document_prompt(self) -> str:
        return "Generate concise Markdown documentation from the request and execution result."

    def build_user_prompt(self, message: str, context: AIContext) -> str:
        parts = [f"User message: {message}"]
        if context.request:
            parts.append(f"Request: {context.request}")
        if context.collection:
            parts.append(f"Collection: {context.collection}")
        if context.environment:
            parts.append(f"Environment: {context.environment}")
        if context.execution_result:
            parts.append(f"Execution: {context.execution_result}")
        return "\n".join(parts)

