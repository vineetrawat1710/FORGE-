from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.context.context_builder import AIContext, AIContextBuilder
from app.ai.providers import build_provider
from app.ai.prompts.prompt_builder import PromptBuilder
from app.ai.tools.implementations import (
    EnvironmentLookupTool,
    ExplainResponseTool,
    GenerateCodeTool,
    GenerateDocumentationTool,
    SearchCollectionsTool,
    SearchRequestsTool,
)
from app.ai.tools.registry import ToolRegistry
from app.models.user import User
from app.schemas.ai import AIChatResponse, AIToolResponse, AIDocumentRequest, AIGenerateCodeRequest, AIGenerateRequestResponse, AIExplainResponseRequest, AISearchResponse
from app.services.collection_service import CollectionService
from app.services.environment_service import EnvironmentService
from app.services.request_service import RequestService
from app.core.config import get_settings
from app.ai.orchestrator.task_classifier import AITask, TaskClassifier


class AIOrchestrator:
    def __init__(self, db: Session, provider=None):
        self.db = db
        settings = get_settings()
        self.provider = provider or build_provider(settings.ai_provider, settings.ai_model)
        self.settings = settings
        self.classifier = TaskClassifier()
        self.context_builder = AIContextBuilder(db)
        self.prompts = PromptBuilder()
        self.registry = ToolRegistry()
        self.request_service = RequestService(db)
        self.collection_service = CollectionService(db)
        self.environment_service = EnvironmentService(db)
        self.registry.register(SearchRequestsTool(self.request_service))
        self.registry.register(SearchCollectionsTool(self.collection_service))
        self.registry.register(GenerateDocumentationTool())
        self.registry.register(GenerateCodeTool())
        self.registry.register(ExplainResponseTool())
        self.registry.register(EnvironmentLookupTool(self.environment_service))

    def generate_request(self, user: User, prompt: str) -> AIGenerateRequestResponse:
        text = prompt.lower()
        method = "POST" if "create" in text or "login" in text else "GET"
        url = "https://example.com"
        if "login" in text:
            url = "https://example.com/login"
        body = "{\"email\":\"{{EMAIL}}\",\"password\":\"{{PASSWORD}}\"}" if method == "POST" else None
        return AIGenerateRequestResponse(
            request={
                "name": "Generated Request",
                "description": prompt,
                "method": method,
                "url": url,
                "body": body,
                "body_type": "json" if body else "none",
                "timeout": 30,
                "follow_redirects": True,
                "verify_ssl": True,
                "headers": [{"key": "Accept", "value": "application/json", "enabled": True}],
                "query_parameters": [],
                "authorization": {"type": "none"},
            }
        )

    def explain_response(self, payload: AIExplainResponseRequest) -> AIChatResponse:
        context = AIContext(user={"id": "0", "username": "system"})
        result = self.registry.get("explain_response").run(
            context,
            {"status_code": payload.status_code, "headers": payload.headers, "body": payload.body},
        )
        reply = result["explanation"]
        if payload.status_code == 401:
            reply = "The request was unauthorized and likely needs valid credentials."
        return AIChatResponse(reply=reply, tools=[AIToolResponse(tool="explain_response", result={"status_code": payload.status_code, "headers": payload.headers})])

    def generate_code(self, payload: AIGenerateCodeRequest) -> dict[str, str]:
        request = payload.request
        return {"language": payload.language, "code": f"curl -X {request.method} '{request.url}'"}

    def document(self, payload: AIDocumentRequest) -> dict[str, str]:
        request = payload.request
        return {"markdown": f"## {request.name}\n\n`{request.method} {request.url}`"}

    def search(self, user: User, query: str) -> AISearchResponse:
        q = query.lower()
        requests = [r for r in self.request_service.list(user) if q in r.name.lower() or q in r.url.lower()]
        collections = [c for c in self.collection_service.list(user) if q in c.name.lower()]
        environments = [e for e in self.environment_service.list(user) if q in e.name.lower()]
        return AISearchResponse(requests=requests, collections=collections, environments=environments)

    def resolve_environment(self, user: User, key: str) -> dict[str, object]:
        environment = self.environment_service.get_active_environment(user.id)
        raw = environment.variables.get(key)
        if raw is None:
            return {"key": key, "value": None}
        return {"key": key, "value": raw.get("value") if isinstance(raw, dict) else raw}

    def chat(self, user: User, message: str, context_request_id: UUID | None = None, context_collection_id: UUID | None = None, context_environment_id: UUID | None = None, task: str | None = None, input_size: int = 0, is_openapi: bool = False) -> AIChatResponse:
        context = self.context_builder.build(user, request_id=context_request_id, collection_id=context_collection_id, environment_id=context_environment_id)
        user_prompt = self.prompts.build_user_prompt(message, context)
        classification = self.classifier.classify(message, task=task, input_size=input_size, is_openapi=is_openapi)
        selected_task = AITask.REASONING if classification.confidence < 0.7 else classification.task
        model = {AITask.REASONING: self.settings.ai_chat_model, AITask.LARGE_CONTEXT: self.settings.ai_large_context_model, AITask.FAST: self.settings.ai_fast_model}[selected_task]
        provider = self.provider if getattr(self.provider, "model", None) == model else build_provider(self.settings.ai_provider, model)
        reply = provider.generate(self.prompts.system_prompt(), user_prompt)
        tools: list[AIToolResponse] = []
        if any(keyword in message.lower() for keyword in ("generate", "create", "login")) or reply.startswith("tool:generate_request"):
            generated = self.generate_request(user, message)
            tools.append(AIToolResponse(tool="generate_request", result=generated.model_dump()))
            reply = f"Generated request draft for {generated.request['name']}."
        return AIChatResponse(reply=reply, tools=tools)
