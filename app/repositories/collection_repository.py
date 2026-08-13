from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.collection import Collection, CollectionTag


class CollectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, collection: Collection) -> Collection:
        self.db.add(collection)
        self.db.commit()
        self.db.refresh(collection)
        return collection

    def get_by_id(self, collection_id: UUID) -> Collection | None:
        stmt = select(Collection).options(selectinload(Collection.tags)).where(Collection.id == collection_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_user(self, user_id: UUID) -> list[Collection]:
        stmt = select(Collection).options(selectinload(Collection.tags)).where(Collection.user_id == user_id).order_by(Collection.created_at.desc())
        return list(self.db.execute(stmt).scalars())

    def update(self, collection: Collection) -> Collection:
        self.db.commit()
        self.db.refresh(collection)
        return collection

    def delete(self, collection: Collection) -> None:
        self.db.delete(collection)
        self.db.commit()

    def replace_tags(self, collection_id: UUID, tags: list[str]) -> None:
        self.db.execute(delete(CollectionTag).where(CollectionTag.collection_id == collection_id))
        for tag in tags:
            self.db.add(CollectionTag(collection_id=collection_id, name=tag))
        self.db.commit()
        self.db.expire_all()
