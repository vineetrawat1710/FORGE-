from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import EnvironmentAccessDeniedError, EnvironmentNotFoundError, RequestNotFoundError
from app.models.environment import Environment
from app.models.request import AuthorizationType, BodyType, Request, RequestAuthorization, RequestHeader, RequestQueryParameter
from app.models.user import User
from app.repositories.request_repository import RequestRepository
from app.schemas.request import (
    RequestAuthorizationBase,
    RequestAuthorizationResponse,
    RequestCreate,
    RequestHeaderBase,
    RequestHeaderResponse,
    RequestQueryParameterBase,
    RequestQueryParameterResponse,
    RequestResponse,
    RequestUpdate,
)
from app.services.environment_service import EnvironmentService


class RequestService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = RequestRepository(db)
        self.environment_service = EnvironmentService(db)

    def _ensure_request_owner(self, request: Request, user_id: UUID) -> None:
        if request.user_id != user_id:
            raise EnvironmentAccessDeniedError("You do not own this request.")

    def _ensure_environment_owner(self, environment_id: UUID | None, user_id: UUID) -> None:
        if environment_id is None:
            return
        environment = self.db.get(Environment, environment_id)
        if environment is None:
            raise EnvironmentNotFoundError("Environment not found.")
        if environment.user_id != user_id:
            raise EnvironmentAccessDeniedError("You do not own this environment.")

    def _build_headers(self, headers: list[RequestHeaderBase]) -> list[RequestHeader]:
        return [RequestHeader(key=item.key, value=item.value, description=item.description, enabled=item.enabled) for item in headers]

    def _build_query_parameters(self, params: list[RequestQueryParameterBase]) -> list[RequestQueryParameter]:
        return [RequestQueryParameter(key=item.key, value=item.value, description=item.description, enabled=item.enabled) for item in params]

    def _build_authorization(self, authorization: RequestAuthorizationBase) -> RequestAuthorization | None:
        if authorization.type == AuthorizationType.NONE:
            return None
        if authorization.type == AuthorizationType.BEARER:
            if not authorization.token:
                raise ValueError("Bearer token is required.")
            return RequestAuthorization(type=authorization.type.value, token=authorization.token)
        if authorization.type == AuthorizationType.BASIC:
            if not authorization.username or not authorization.password:
                raise ValueError("Basic authentication requires username and password.")
            return RequestAuthorization(type=authorization.type.value, username=authorization.username, password=authorization.password)
        if authorization.type == AuthorizationType.API_KEY:
            if not authorization.api_key_name or not authorization.api_key_value or not authorization.api_key_in:
                raise ValueError("API key authentication requires name, value, and location.")
            return RequestAuthorization(
                type=authorization.type.value,
                api_key_name=authorization.api_key_name,
                api_key_value=authorization.api_key_value,
                api_key_in=authorization.api_key_in,
            )
        raise ValueError("Unsupported authorization type.")

    def _to_response(self, request: Request) -> RequestResponse:
        headers = [RequestHeaderResponse.model_validate(header) for header in request.headers]
        query_parameters = [RequestQueryParameterResponse.model_validate(item) for item in request.query_parameters]
        authorization = (
            RequestAuthorizationResponse.model_validate(request.authorization)
            if request.authorization is not None
            else None
        )
        return RequestResponse(
            id=request.id,
            user_id=request.user_id,
            collection_id=request.collection_id,
            environment_id=request.environment_id,
            name=request.name,
            description=request.description,
            method=request.method,
            url=request.url,
            body=request.body,
            body_type=request.body_type,
            timeout=request.timeout,
            follow_redirects=request.follow_redirects,
            verify_ssl=request.verify_ssl,
            is_favorite=request.is_favorite,
            created_at=request.created_at,
            updated_at=request.updated_at,
            headers=headers,
            query_parameters=query_parameters,
            authorization=authorization,
        )

    def create(self, user: User, payload: RequestCreate) -> RequestResponse:
        self._ensure_environment_owner(payload.environment_id, user.id)
        request = Request(
            user_id=user.id,
            collection_id=payload.collection_id,
            environment_id=payload.environment_id,
            name=payload.name,
            description=payload.description,
            method=payload.method.value,
            url=str(payload.url),
            body=payload.body,
            body_type=payload.body_type.value,
            timeout=payload.timeout,
            follow_redirects=payload.follow_redirects,
            verify_ssl=payload.verify_ssl,
            is_favorite=payload.is_favorite,
        )
        created = self.repository.create(request)
        self.repository.add_headers(created.id, self._build_headers(payload.headers))
        self.repository.add_query_parameters(created.id, self._build_query_parameters(payload.query_parameters))
        self.repository.set_authorization(created.id, self._build_authorization(payload.authorization))
        return self._to_response(self.repository.get_by_id(created.id) or created)

    def list(self, user: User) -> list[RequestResponse]:
        return [self._to_response(item) for item in self.repository.list_by_user(user.id)]

    def get(self, user: User, request_id: UUID) -> RequestResponse:
        request = self.repository.get_by_id(request_id)
        if request is None:
            raise RequestNotFoundError("Request not found.")
        self._ensure_request_owner(request, user.id)
        return self._to_response(request)

    def update(self, user: User, request_id: UUID, payload: RequestUpdate) -> RequestResponse:
        request = self.repository.get_by_id(request_id)
        if request is None:
            raise RequestNotFoundError("Request not found.")
        self._ensure_request_owner(request, user.id)

        data = payload.model_dump(exclude_unset=True, exclude={"headers", "query_parameters", "authorization"})
        if "environment_id" in data:
            self._ensure_environment_owner(data["environment_id"], user.id)
        if "method" in data:
            data["method"] = data["method"].value
        if "url" in data and data["url"] is not None:
            data["url"] = str(data["url"])
        if "body_type" in data and data["body_type"] is not None:
            data["body_type"] = data["body_type"].value
        for key, value in data.items():
            setattr(request, key, value)
        if payload.headers is not None:
            self.repository.replace_headers(request.id, self._build_headers(payload.headers))
        if payload.query_parameters is not None:
            self.repository.replace_query_parameters(request.id, self._build_query_parameters(payload.query_parameters))
        if payload.authorization is not None:
            self.repository.replace_authorization(request.id, self._build_authorization(payload.authorization))
        self.db.commit()
        return self._to_response(self.repository.get_by_id(request.id) or request)

    def delete(self, user: User, request_id: UUID) -> None:
        request = self.repository.get_by_id(request_id)
        if request is None:
            raise RequestNotFoundError("Request not found.")
        self._ensure_request_owner(request, user.id)
        self.repository.delete(request)
