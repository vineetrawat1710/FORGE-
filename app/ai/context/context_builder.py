from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.request import Request
from app.models.user import User
from app.services.collection_service import CollectionService
from app.services.environment_service import EnvironmentService
from app.services.request_service import RequestService


@dataclass
class AIContext:
    user: dict[str, object]
    request: dict[str, object] | None = None
    collection: dict[str, object] | None = None
    environment: dict[str, object] | None = None
    execution_result: dict[str, object] | None = None
    conversation: list[dict[str, str]] = field(default_factory=list)


class AIContextBuilder:
    def __init__(self, db: Session):
        self.request_service = RequestService(db)
        self.collection_service = CollectionService(db)
        self.environment_service = EnvironmentService(db)

    def build(
        self,
        user: User,
        request_id: UUID | None = None,
        collection_id: UUID | None = None,
        environment_id: UUID | None = None,
        execution_result: dict[str, object] | None = None,
        conversation: list[dict[str, str]] | None = None,
    ) -> AIContext:
        ctx = AIContext(user={"id": str(user.id), "username": user.username})
        if request_id is not None:
            request = self.request_service.get(user, request_id)
            ctx.request = {"id": str(request.id), "name": request.name, "method": request.method, "url": request.url, "headers": [{"key": h.key, "enabled": h.enabled} for h in request.headers]}
        if collection_id is not None:
            collection = self.collection_service.get(user, collection_id)
            ctx.collection = {"id": str(collection.id), "name": collection.name}
        if environment_id is not None:
            environment = self.environment_service.get(user, environment_id)
            ctx.environment = {"id": str(environment.id), "name": environment.name, "variables": list((environment.variables or {}).keys())}
        ctx.execution_result = execution_result
        ctx.conversation = (conversation or [])[-10:]
        return ctx

