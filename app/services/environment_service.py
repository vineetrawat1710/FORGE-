import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ActiveEnvironmentNotFoundError, EnvironmentAccessDeniedError, EnvironmentNotFoundError
from app.models.environment import Environment
from app.models.user import User
from app.repositories.environment_repository import EnvironmentRepository
from app.schemas.environment import EnvironmentCreate, EnvironmentListItem, EnvironmentResponse, EnvironmentUpdate


VARIABLE_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


class EnvironmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = EnvironmentRepository(db)

    def _ensure_ownership(self, environment: Environment, user_id: UUID) -> None:
        if environment.user_id != user_id:
            raise EnvironmentAccessDeniedError("You do not own this environment.")

    def _mask_variables(self, variables: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
        masked: dict[str, dict[str, object]] = {}
        for key, value in variables.items():
            if isinstance(value, dict):
                masked_value = dict(value)
                if masked_value.get("secret") is True and "value" in masked_value:
                    masked_value["value"] = "****"
                masked[key] = masked_value
        return masked

    def _to_response(self, environment: Environment) -> EnvironmentResponse:
        return EnvironmentResponse(
            id=environment.id,
            user_id=environment.user_id,
            name=environment.name,
            description=environment.description,
            variables=self._mask_variables(environment.variables or {}),
            is_active=environment.is_active,
            created_at=environment.created_at,
            updated_at=environment.updated_at,
        )

    def _to_list_item(self, environment: Environment) -> EnvironmentListItem:
        return EnvironmentListItem.model_validate(environment)

    def create(self, user: User, payload: EnvironmentCreate) -> EnvironmentResponse:
        if payload.is_active:
            self.repository.unset_active_for_user(user.id)

        environment = Environment(
            user_id=user.id,
            name=payload.name,
            description=payload.description,
            variables=payload.variables,
            is_active=payload.is_active,
        )
        created = self.repository.create(environment)
        return self._to_response(created)

    def list(self, user: User) -> list[EnvironmentListItem]:
        return [self._to_list_item(environment) for environment in self.repository.list_by_user(user.id)]

    def get(self, user: User, environment_id: UUID) -> EnvironmentResponse:
        environment = self.repository.get_by_id(environment_id)
        if environment is None:
            raise EnvironmentNotFoundError("Environment not found.")
        self._ensure_ownership(environment, user.id)
        return self._to_response(environment)

    def update(self, user: User, environment_id: UUID, payload: EnvironmentUpdate) -> EnvironmentResponse:
        environment = self.repository.get_by_id(environment_id)
        if environment is None:
            raise EnvironmentNotFoundError("Environment not found.")
        self._ensure_ownership(environment, user.id)

        data = payload.model_dump(exclude_unset=True)
        updated = self.repository.update(environment, data)
        return self._to_response(updated)

    def delete(self, user: User, environment_id: UUID) -> None:
        environment = self.repository.get_by_id(environment_id)
        if environment is None:
            raise EnvironmentNotFoundError("Environment not found.")
        self._ensure_ownership(environment, user.id)
        self.repository.delete(environment)

    def activate(self, user: User, environment_id: UUID) -> EnvironmentResponse:
        environment = self.repository.get_by_id(environment_id)
        if environment is None:
            raise EnvironmentNotFoundError("Environment not found.")
        self._ensure_ownership(environment, user.id)

        current = self.repository.get_active_by_user(user.id)
        if current is not None and current.id != environment.id:
            current.is_active = False
            self.repository.update(current, {"is_active": False})

        environment.is_active = True
        updated = self.repository.update(environment, {"is_active": True})
        return self._to_response(updated)

    def deactivate(self, user: User) -> None:
        current = self.repository.get_active_by_user(user.id)
        if current is not None:
            current.is_active = False
            self.repository.update(current, {"is_active": False})

    def get_active_environment(self, user_id: UUID) -> Environment:
        environment = self.repository.get_active_by_user(user_id)
        if environment is None:
            raise ActiveEnvironmentNotFoundError("No active environment found.")
        return environment

    def resolve_variables(self, text: str, user_id: UUID) -> str:
        environment = self.get_active_environment(user_id)
        variables = environment.variables or {}

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            raw = variables.get(key, {})
            if isinstance(raw, dict):
                value = raw.get("value")
                if value is not None:
                    return str(value)
            return match.group(0)

        return VARIABLE_PATTERN.sub(replace, text)
