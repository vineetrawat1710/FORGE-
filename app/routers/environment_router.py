from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.schemas.environment import EnvironmentCreate, EnvironmentListItem, EnvironmentResponse, EnvironmentUpdate
from app.schemas.user import UserResponse
from app.services.environment_service import EnvironmentService

router = APIRouter(prefix="/api/v1/environments", tags=["environments"])


@router.get("", response_model=list[EnvironmentListItem])
def list_environments(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EnvironmentListItem]:
    return EnvironmentService(db).list(current_user)


@router.post("", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
def create_environment(
    payload: EnvironmentCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnvironmentResponse:
    return EnvironmentService(db).create(current_user, payload)


@router.get("/{environment_id}", response_model=EnvironmentResponse)
def get_environment(
    environment_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnvironmentResponse:
    return EnvironmentService(db).get(current_user, environment_id)


@router.patch("/{environment_id}", response_model=EnvironmentResponse)
def update_environment(
    environment_id: UUID,
    payload: EnvironmentUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnvironmentResponse:
    return EnvironmentService(db).update(current_user, environment_id, payload)


@router.delete("/{environment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_environment(
    environment_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    EnvironmentService(db).delete(current_user, environment_id)


@router.post("/{environment_id}/activate", response_model=EnvironmentResponse)
def activate_environment(
    environment_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnvironmentResponse:
    return EnvironmentService(db).activate(current_user, environment_id)

@router.post("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_environment(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    EnvironmentService(db).deactivate(current_user)
