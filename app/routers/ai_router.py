from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.schemas.ai import AIChatRequest, AIDocumentRequest, AIGenerateCodeRequest, AIGenerateRequestRequest, AIExplainResponseRequest, AISearchRequest
from app.schemas.user import UserResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.post("/chat")
def chat(payload: AIChatRequest, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIService(db).chat(
        current_user,
        payload.message,
        UUID(payload.context_request_id) if payload.context_request_id else None,
        UUID(payload.context_collection_id) if payload.context_collection_id else None,
        UUID(payload.context_environment_id) if payload.context_environment_id else None,
        payload.task,
        payload.input_size,
        payload.is_openapi,
    )


@router.post("/generate-request")
def generate_request(payload: AIGenerateRequestRequest, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIService(db).generate_request(current_user, payload.prompt)


@router.post("/explain-response")
def explain_response(payload: AIExplainResponseRequest, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIService(db).explain_response(payload)


@router.post("/generate-code")
def generate_code(payload: AIGenerateCodeRequest, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIService(db).generate_code(payload)


@router.post("/document")
def document(payload: AIDocumentRequest, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIService(db).document(payload)


@router.post("/search")
def search(payload: AISearchRequest, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    return AIService(db).search(current_user, payload.query)
