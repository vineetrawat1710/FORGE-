from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.schemas.request import GlobalHistoryPage, GlobalHistoryDetailResponse, ExecutionResponse
from app.schemas.user import UserResponse
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/api/v1/history", tags=["history"])


@router.get("", response_model=GlobalHistoryPage)
def list_global_history(
    search: Optional[str] = Query(None, max_length=255),
    methods: Optional[list[str]] = Query(None),
    status_classes: Optional[list[str]] = Query(None),
    duration_min: Optional[int] = Query(None),
    duration_max: Optional[int] = Query(None),
    date_min: Optional[datetime] = Query(None),
    collection_id: Optional[UUID] = Query(None),
    environment_id: Optional[UUID] = Query(None),
    execution_status: Optional[str] = Query(None, max_length=30),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    items, total = ExecutionService(db).list_global_history(
        current_user,
        search=search,
        methods=methods,
        status_classes=status_classes,
        duration_min=duration_min,
        duration_max=duration_max,
        date_min=date_min,
        collection_id=collection_id,
        environment_id=environment_id,
        execution_status=execution_status,
        limit=limit,
        offset=offset,
    )
    return GlobalHistoryPage(items=items, total=total, limit=limit, offset=offset)

@router.get("/{history_id}", response_model=GlobalHistoryDetailResponse)
def get_global_history_item(
    history_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ExecutionService(db).get_global_history_item(current_user, history_id)

@router.post("/{history_id}/replay", response_model=ExecutionResponse)
async def replay_history_item(
    history_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutionResponse:
    return await ExecutionService(db).replay(current_user, history_id)
