from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.environment import Environment


class EnvironmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, environment: Environment) -> Environment:
        self.db.add(environment)
        self.db.commit()
        self.db.refresh(environment)
        return environment

    def get_by_id(self, environment_id: UUID) -> Environment | None:
        return self.db.get(Environment, environment_id)

    def list_by_user(self, user_id: UUID) -> list[Environment]:
        return list(self.db.execute(select(Environment).where(Environment.user_id == user_id).order_by(Environment.created_at.desc())).scalars())

    def get_active_by_user(self, user_id: UUID) -> Environment | None:
        stmt = select(Environment).where(Environment.user_id == user_id, Environment.is_active.is_(True))
        return self.db.execute(stmt).scalar_one_or_none()

    def unset_active_for_user(self, user_id: UUID) -> None:
        stmt = update(Environment).where(Environment.user_id == user_id, Environment.is_active.is_(True)).values(is_active=False)
        self.db.execute(stmt)
        self.db.commit()

    def update(self, environment: Environment, data: dict) -> Environment:
        for key, value in data.items():
            if hasattr(environment, key):
                setattr(environment, key, value)
        self.db.commit()
        self.db.refresh(environment)
        return environment

    def delete(self, environment: Environment) -> None:
        self.db.delete(environment)
        self.db.commit()
