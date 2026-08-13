from __future__ import annotations

import json
from uuid import UUID
from urllib.parse import urljoin, urlparse

from sqlalchemy.orm import Session

from app.core.exceptions import ExportError, ImportLimitExceededError
from app.models.collection import Collection
from app.models.request import AuthorizationType, BodyType, Request, RequestAuthorization, RequestHeader, RequestQueryParameter
from app.models.user import User
from app.schemas.import_export import ImportSummary
from app.schemas.request import RequestAuthorizationBase, RequestCreate, RequestHeaderBase, RequestQueryParameterBase
from app.services.collection_service import CollectionService
from app.utils.curl_parser import parse_curl_command
from app.utils.openapi_parser import parse_openapi_document
from app.utils.postman_parser import parse_postman_collection


class ImportExportService:
    def __init__(self, db: Session):
        self.db = db
        self.collection_service = CollectionService(db)

    def _limit_requests(self, count: int) -> None:
        if count > 100:
            raise ImportLimitExceededError("Import exceeds the maximum request count.")

    def _build_request(self, user: User, collection_id: UUID | None, parsed) -> RequestCreate:
        body = None
        body_type = BodyType.NONE
        if parsed.body is not None:
            body = parsed.body.get("raw")
            mode = parsed.body.get("mode")
            body_type = {
                "raw": BodyType.TEXT,
                "json": BodyType.JSON,
                "xml": BodyType.XML,
                "urlencoded": BodyType.FORM,
                "multipart": BodyType.MULTIPART,
            }.get(mode, BodyType.TEXT)
        auth = RequestAuthorizationBase(type=AuthorizationType.NONE)
        if parsed.authorization:
            auth_type = str(parsed.authorization.get("type") or "none").lower()
            if auth_type == "bearer":
                auth = RequestAuthorizationBase(type=AuthorizationType.BEARER, token=parsed.authorization.get("token"))
            elif auth_type == "basic":
                auth = RequestAuthorizationBase(
                    type=AuthorizationType.BASIC,
                    username=parsed.authorization.get("username"),
                    password=parsed.authorization.get("password"),
                )
            elif auth_type == "api_key":
                auth = RequestAuthorizationBase(
                    type=AuthorizationType.API_KEY,
                    api_key_name=parsed.authorization.get("key") or parsed.authorization.get("apiKey"),
                    api_key_value=parsed.authorization.get("value"),
                    api_key_in=parsed.authorization.get("in"),
                )
        return RequestCreate(
            name=parsed.name,
            description=parsed.description,
            method=parsed.method,
            url=parsed.url,
            body=body,
            body_type=body_type,
            headers=[RequestHeaderBase(**header) for header in parsed.headers],
            query_parameters=[RequestQueryParameterBase(**param) for param in parsed.query_parameters],
            authorization=auth,
            collection_id=collection_id,
        )

    def _normalize_url(self, base_url: str | None, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return urljoin((base_url or "https://example.com").rstrip("/") + "/", url.lstrip("/"))

    def _persist_collection_and_requests(self, user: User, collection_name: str, description: str | None, requests: list[RequestCreate]) -> UUID:
        collection = Collection(user_id=user.id, name=collection_name, description=description, is_favorite=False)
        self.db.add(collection)
        self.db.flush()
        for payload in requests:
            request = Request(
                user_id=user.id,
                collection_id=collection.id,
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
            self.db.add(request)
            self.db.flush()
            for header in payload.headers:
                self.db.add(RequestHeader(request_id=request.id, key=header.key, value=header.value, enabled=header.enabled))
            for query_parameter in payload.query_parameters:
                self.db.add(
                    RequestQueryParameter(
                        request_id=request.id,
                        key=query_parameter.key,
                        value=query_parameter.value,
                        enabled=query_parameter.enabled,
                    )
                )
            if payload.authorization.type != AuthorizationType.NONE:
                auth = RequestAuthorization(request_id=request.id, type=payload.authorization.type.value)
                if payload.authorization.type == AuthorizationType.BEARER:
                    auth.token = payload.authorization.token
                elif payload.authorization.type == AuthorizationType.BASIC:
                    auth.username = payload.authorization.username
                    auth.password = payload.authorization.password
                elif payload.authorization.type == AuthorizationType.API_KEY:
                    auth.api_key_name = payload.authorization.api_key_name
                    auth.api_key_value = payload.authorization.api_key_value
                    auth.api_key_in = payload.authorization.api_key_in
                self.db.add(auth)
        self.db.commit()
        return collection.id

    def import_postman(self, user: User, content: str, collection_name: str | None = None) -> ImportSummary:
        parsed = parse_postman_collection(content)
        self._limit_requests(len(parsed.requests))
        request_payloads = [self._build_request(user, None, item) for item in parsed.requests]
        collection_id = self._persist_collection_and_requests(user, collection_name or parsed.name, parsed.description, request_payloads)
        return ImportSummary(source_type="postman", collections_created=1, requests_created=len(request_payloads), skipped_items=0, collection_id=str(collection_id))

    def import_openapi(self, user: User, content: str, collection_name: str | None = None) -> ImportSummary:
        parsed = parse_openapi_document(content)
        self._limit_requests(len(parsed.requests))
        request_payloads = []
        for item in parsed.requests:
            item.url = self._normalize_url(parsed.base_url, item.url)
            request_payloads.append(self._build_request(user, None, item))
        collection_id = self._persist_collection_and_requests(user, collection_name or parsed.name, parsed.description, request_payloads)
        return ImportSummary(source_type="openapi", collections_created=1, requests_created=len(request_payloads), skipped_items=0, collection_id=str(collection_id))

    def import_curl(self, user: User, content: str, collection_id: UUID | None = None) -> ImportSummary:
        parsed = parse_curl_command(content)
        payload = self._build_request(user, collection_id, parsed)
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
        self.db.add(request)
        self.db.flush()
        for header in payload.headers:
            self.db.add(RequestHeader(request_id=request.id, key=header.key, value=header.value, enabled=header.enabled))
        for query_parameter in payload.query_parameters:
            self.db.add(RequestQueryParameter(request_id=request.id, key=query_parameter.key, value=query_parameter.value, enabled=query_parameter.enabled))
        if payload.authorization.type != AuthorizationType.NONE:
            auth = RequestAuthorization(request_id=request.id, type=payload.authorization.type.value)
            if payload.authorization.type == AuthorizationType.BEARER:
                auth.token = payload.authorization.token
            elif payload.authorization.type == AuthorizationType.BASIC:
                auth.username = payload.authorization.username
                auth.password = payload.authorization.password
            elif payload.authorization.type == AuthorizationType.API_KEY:
                auth.api_key_name = payload.authorization.api_key_name
                auth.api_key_value = payload.authorization.api_key_value
                auth.api_key_in = payload.authorization.api_key_in
            self.db.add(auth)
        self.db.commit()
        return ImportSummary(source_type="curl", collections_created=0, requests_created=1, skipped_items=0, collection_id=str(collection_id) if collection_id else None)

    def export_postman(self, user: User, collection_id: UUID) -> dict:
        collection = self.collection_service.get(user, collection_id)
        requests = self.db.query(Request).filter(Request.user_id == user.id, Request.collection_id == collection_id).all()
        items = []
        for request in requests:
            if request.collection_id != collection_id:
                continue
            items.append(
                {
                    "name": request.name,
                    "request": {
                        "method": request.method,
                        "header": [{"key": header.key, "value": header.value} for header in request.headers],
                        "url": {
                            "raw": request.url,
                            "host": [request.url],
                            "query": [{"key": qp.key, "value": qp.value} for qp in request.query_parameters],
                        },
                    },
                }
            )
        return {
            "info": {"name": collection.name, "_postman_id": str(collection.id), "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
            "item": items,
        }

    def export_openapi(self, user: User, collection_id: UUID) -> dict:
        collection = self.collection_service.get(user, collection_id)
        requests = self.db.query(Request).filter(Request.user_id == user.id, Request.collection_id == collection_id).all()
        paths: dict[str, dict[str, object]] = {}
        for request in requests:
            if request.collection_id != collection_id:
                continue
            parsed_url = urlparse(request.url)
            path = parsed_url.path or "/"
            paths.setdefault(path, {})[request.method.lower()] = {
                "summary": request.name,
                "description": request.description,
                "responses": {"200": {"description": "Success"}},
            }
        return {"openapi": "3.0.3", "info": {"title": collection.name, "version": "1.0.0"}, "paths": paths}

    def export_curl(self, user: User, request_id: UUID) -> str:
        request = self.db.query(Request).filter(Request.id == request_id).one_or_none()
        if request is None:
            raise ExportError("Request not found.")
        if request.user_id != user.id:
            raise ExportError("You do not own this request.")
        parts = ["curl", f"'{request.url}'", "-X", request.method]
        for header in request.headers:
            parts.extend(["-H", f"'{header.key}: {header.value}'"])
        if request.body:
            parts.extend(["--data-raw", f"'{request.body}'"])
        auth = request.authorization
        if auth and auth.type == AuthorizationType.BEARER.value and auth.token:
            parts.extend(["-H", f"'Authorization: Bearer {auth.token}'"])
        elif auth and auth.type == AuthorizationType.BASIC.value and auth.username and auth.password:
            parts.extend(["-u", f"'{auth.username}:{auth.password}'"])
        return " ".join(parts)
