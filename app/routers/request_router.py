from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.schemas.request import ExecutionHistoryPage, ExecutionHistoryResponse, ExecutionResponse, RequestCreate, RequestResponse, RequestUpdate
from app.schemas.user import UserResponse
from app.services.request_service import RequestService
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/api/v1/requests", tags=["requests"])


@router.get("", response_model=list[RequestResponse])
def list_requests(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RequestResponse]:
    return RequestService(db).list(current_user)


@router.post("", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestResponse:
    return RequestService(db).create(current_user, payload)


@router.get("/{request_id}", response_model=RequestResponse)
def get_request(
    request_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestResponse:
    return RequestService(db).get(current_user, request_id)


@router.patch("/{request_id}", response_model=RequestResponse)
def update_request(
    request_id: UUID,
    payload: RequestUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestResponse:
    return RequestService(db).update(current_user, request_id, payload)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_request(
    request_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    RequestService(db).delete(current_user, request_id)


@router.post("/{request_id}/execute", response_model=ExecutionResponse)
async def execute_request(
    request_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutionResponse:
    return await ExecutionService(db).execute(current_user, request_id)


@router.get("/{request_id}/history", response_model=ExecutionHistoryPage)
def list_request_history(
    request_id: UUID,
    search: str | None = None,
    status_code: int | None = None,
    execution_status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutionHistoryPage:
    items, total = ExecutionService(db).list_history(current_user, request_id, search=search, status_code=status_code, execution_status=execution_status, limit=limit, offset=offset)
    return ExecutionHistoryPage(
        items=[ExecutionHistoryResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
