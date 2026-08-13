from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai.orchestrator.ai_orchestrator import AIOrchestrator
from app.models.user import User
from app.schemas.ai import AIChatResponse, AIDocumentRequest, AIGenerateCodeRequest, AIGenerateRequestResponse, AIExplainResponseRequest, AISearchResponse


class AIService:
    def __init__(self, db: Session, provider=None):
        self.orchestrator = AIOrchestrator(db, provider=provider)

    def generate_request(self, user: User, prompt: str) -> AIGenerateRequestResponse:
        return self.orchestrator.generate_request(user, prompt)

    def explain_response(self, payload: AIExplainResponseRequest) -> AIChatResponse:
        return self.orchestrator.explain_response(payload)

    def generate_code(self, payload: AIGenerateCodeRequest) -> dict[str, str]:
        return self.orchestrator.generate_code(payload)

    def document(self, payload: AIDocumentRequest) -> dict[str, str]:
        return self.orchestrator.document(payload)

    def search(self, user: User, query: str) -> AISearchResponse:
        return self.orchestrator.search(user, query)

    def chat(self, user: User, message: str, context_request_id=None, context_collection_id=None, context_environment_id=None, task=None, input_size=0, is_openapi=False) -> AIChatResponse:
        return self.orchestrator.chat(user, message, context_request_id, context_collection_id, context_environment_id, task, input_size, is_openapi)
