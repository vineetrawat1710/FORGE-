from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        result = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        return result

    def get_by_username(self, username: str) -> User | None:
        result = self.db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        return result

    def get_by_id(self, user_id: UUID) -> User | None:
        result = self.db.get(User, user_id)
        return result

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
