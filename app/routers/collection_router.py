from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.schemas.collection import CollectionCreate, CollectionResponse, CollectionUpdate
from app.schemas.user import UserResponse
from app.services.collection_service import CollectionService

router = APIRouter(prefix="/api/v1/collections", tags=["collections"])


@router.get("", response_model=list[CollectionResponse])
def list_collections(current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CollectionResponse]:
    return CollectionService(db).list(current_user)


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(payload: CollectionCreate, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> CollectionResponse:
    return CollectionService(db).create(current_user, payload)


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(collection_id: UUID, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> CollectionResponse:
    return CollectionService(db).get(current_user, collection_id)


@router.patch("/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: UUID,
    payload: CollectionUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionResponse:
    return CollectionService(db).update(current_user, collection_id, payload)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: UUID, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    CollectionService(db).delete(current_user, collection_id)


@router.post("/{collection_id}/favorite", response_model=CollectionResponse)
def favorite_collection(collection_id: UUID, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> CollectionResponse:
    return CollectionService(db).set_favorite(current_user, collection_id, True)


@router.delete("/{collection_id}/favorite", response_model=CollectionResponse)
def unfavorite_collection(collection_id: UUID, current_user: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)) -> CollectionResponse:
    return CollectionService(db).set_favorite(current_user, collection_id, False)
