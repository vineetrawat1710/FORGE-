from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import CollectionAccessDeniedError, CollectionNotFoundError
from app.models.collection import Collection, CollectionTag
from app.models.user import User
from app.repositories.collection_repository import CollectionRepository
from app.schemas.collection import CollectionCreate, CollectionResponse, CollectionUpdate


class CollectionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CollectionRepository(db)

    def _ensure_owner(self, collection: Collection, user_id: UUID) -> None:
        if collection.user_id != user_id:
            raise CollectionAccessDeniedError("You do not own this collection.")

    def _to_response(self, collection: Collection) -> CollectionResponse:
        return CollectionResponse.model_validate(collection)

    def create(self, user: User, payload: CollectionCreate) -> CollectionResponse:
        collection = Collection(user_id=user.id, name=payload.name, description=payload.description, is_favorite=payload.is_favorite)
        created = self.repository.create(collection)
        self.repository.replace_tags(created.id, payload.tags)
        return self._to_response(self.repository.get_by_id(created.id) or created)

    def list(self, user: User) -> list[CollectionResponse]:
        return [self._to_response(item) for item in self.repository.list_by_user(user.id)]

    def get(self, user: User, collection_id: UUID) -> CollectionResponse:
        collection = self.repository.get_by_id(collection_id)
        if collection is None:
            raise CollectionNotFoundError("Collection not found.")
        self._ensure_owner(collection, user.id)
        return self._to_response(collection)

    def update(self, user: User, collection_id: UUID, payload: CollectionUpdate) -> CollectionResponse:
        collection = self.repository.get_by_id(collection_id)
        if collection is None:
            raise CollectionNotFoundError("Collection not found.")
        self._ensure_owner(collection, user.id)
        data = payload.model_dump(exclude_unset=True)
        tags = data.pop("tags", None)
        for key, value in data.items():
            setattr(collection, key, value)
        self.db.commit()
        self.db.refresh(collection)
        if tags is not None:
            self.repository.replace_tags(collection.id, tags)
        return self._to_response(self.repository.get_by_id(collection_id) or collection)

    def set_favorite(self, user: User, collection_id: UUID, is_favorite: bool) -> CollectionResponse:
        collection = self.repository.get_by_id(collection_id)
        if collection is None:
            raise CollectionNotFoundError("Collection not found.")
        self._ensure_owner(collection, user.id)
        collection.is_favorite = is_favorite
        self.db.commit()
        self.db.refresh(collection)
        return self._to_response(collection)

    def delete(self, user: User, collection_id: UUID) -> None:
        collection = self.repository.get_by_id(collection_id)
        if collection is None:
            raise CollectionNotFoundError("Collection not found.")
        self._ensure_owner(collection, user.id)
        self.repository.delete(collection)
