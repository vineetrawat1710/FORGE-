from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse
import uuid
import uuid
from uuid import UUID
import httpx
import re
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    ConnectionFailureError,
    DNSResolutionError,
    EnvironmentAccessDeniedError,
    EnvironmentNotFoundError,
    InvalidRequestURLError,
    RedirectLimitExceededError,
    RequestCancelledError,
    RequestExecutionError,
    RequestNotFoundError,
    RequestTimeoutError,
    ResponseTooLargeError,
    SSLVerificationError,
)
from app.models.request import AuthorizationType, BodyType, Request, RequestExecutionHistory, RequestHeader, RequestQueryParameter, RequestAuthorization
from app.models.user import User
from app.repositories.request_repository import RequestRepository
from app.schemas.request import ExecutionResponse, ConsoleLog
from app.services.environment_service import EnvironmentService

settings = get_settings()
from app.core.logging import get_logger

logger = get_logger("execution")


@dataclass
class PreparedRequest:
    method: str
    url: str
    headers: dict[str, str]
    query_params: list[tuple[str, str]]
    content: bytes | None
    timeout: float
    follow_redirects: bool
    verify_ssl: bool
    cookies: dict[str, str]


class ExecutionService:
    def __init__(self, db: Session, client: httpx.AsyncClient | None = None):
        self.db = db
        self.repository = RequestRepository(db)
        self.environment_service = EnvironmentService(db)
        self._client = client

    def _load_request(self, request_id: UUID) -> Request:
        request = self.repository.get_by_id(request_id)
        if request is None:
            raise RequestNotFoundError("Request not found.")
        return request

    def _verify_owner(self, request: Request, user_id: UUID) -> None:
        if request.user_id != user_id:
            raise EnvironmentAccessDeniedError("You do not own this request.")

    def _get_active_environment(self, user_id: UUID) -> Environment | None:
        return self.environment_service.repository.get_active_by_user(user_id)

    def _resolve_nested(self, text: str, variables: dict[str, dict[str, Any]] | None, console_logs: list[ConsoleLog] | None = None, mask_secrets: bool = False) -> str:
        if not text or "{{" not in text:
            return text
            
        current = text
        for _ in range(10):
            previous = current
            matches = list(re.finditer(r"\{\{([a-zA-Z0-9_]+)\}\}", current))
            if not matches:
                break
                
            for match in matches:
                var_name = match.group(1)
                
                if variables is None:
                    msg = f"Variable '{var_name}' cannot be resolved because no environment is active. Select an environment or replace {{{{{var_name}}}}} with a literal value."
                    if console_logs is not None:
                        console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="ERROR", message=msg))
                    raise RequestExecutionError(msg)
                    
                var_dict = variables.get(var_name)
                if not var_dict:
                    msg = f"Variable '{var_name}' was not found in the active environment."
                    if console_logs is not None:
                        console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="ERROR", message=msg))
                    raise RequestExecutionError(msg)
                    
                if not var_dict.get("enabled", True):
                    msg = f"Variable '{var_name}' is disabled in the active environment."
                    if console_logs is not None:
                        console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="WARNING", message=msg))
                    raise RequestExecutionError(msg)
                    
                if console_logs is not None:
                    console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="INFO", message=f"Resolved variable: {var_name}"))
                    
                val = str(var_dict.get("value", ""))
                if mask_secrets and var_dict.get("secret", False):
                    val = "••••••••"
                current = current.replace(match.group(0), val)
                
            if current == previous:
                break
        else:
            msg = "Circular reference detected in environment variables."
            if console_logs is not None:
                console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="ERROR", message=msg))
            raise RequestExecutionError(msg)
            
        return current

    def _validate_url(self, raw_url: str) -> str:
        parsed = urlparse(raw_url)
        logger.info(f"validate_url: parsed_hostname={parsed.hostname} scheme={parsed.scheme} port={parsed.port}")
        if parsed.scheme not in {"http", "https"}:
            raise InvalidRequestURLError("Only http and https URLs are allowed.")
        if not parsed.hostname:
            raise InvalidRequestURLError("Invalid URL.")
        try:
            infos = socket.getaddrinfo(parsed.hostname, parsed.port)
        except socket.gaierror as exc:
            raise DNSResolutionError("DNS resolution failed.") from exc
        logger.info(f"validate_url: resolved {parsed.hostname} -> {[info[4][0] for info in infos]}")
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            flags = {"is_loopback": ip.is_loopback, "is_private": ip.is_private, "is_link_local": ip.is_link_local}
            logger.info(f"validate_url: checking ip={ip} flags={flags} allow_localhost_targets={settings.allow_localhost_targets_enabled()}")
            if ip.is_loopback or ip.is_private or ip.is_link_local:
                # Allow localhost/loopback/private targets only when explicitly enabled
                if not settings.allow_localhost_targets_enabled():
                    logger.info(f"validate_url: rejecting ip={ip} for url={raw_url}")
                    raise InvalidRequestURLError("Target host is not allowed.")
        return raw_url

    def _serialize_headers(self, request: Request, variables: dict[str, dict[str, Any]] | None, console_logs: list[ConsoleLog] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        for item in request.headers:
            if item.enabled:
                headers[item.key] = self._resolve_nested(item.value, variables, console_logs)
        return headers

    def _serialize_query_parameters(self, request: Request, variables: dict[str, dict[str, Any]] | None, console_logs: list[ConsoleLog] | None = None) -> list[tuple[str, str]]:
        params: list[tuple[str, str]] = []
        for item in request.query_parameters:
            if item.enabled:
                params.append((item.key, self._resolve_nested(item.value, variables, console_logs)))
        return params

    def _serialize_body(self, request: Request, variables: dict[str, dict[str, Any]] | None, console_logs: list[ConsoleLog] | None = None) -> tuple[bytes | None, dict[str, str]]:
        if request.body is None or request.body_type == BodyType.NONE.value:
            return None, {}
        body = self._resolve_nested(request.body, variables, console_logs)
        if request.body_type == BodyType.JSON.value:
            return body.encode("utf-8"), {"Content-Type": "application/json"}
        if request.body_type == BodyType.TEXT.value:
            return body.encode("utf-8"), {"Content-Type": "text/plain"}
        if request.body_type == BodyType.XML.value:
            return body.encode("utf-8"), {"Content-Type": "application/xml"}
        if request.body_type == BodyType.FORM.value:
            return body.encode("utf-8"), {"Content-Type": "application/x-www-form-urlencoded"}
        if request.body_type == BodyType.MULTIPART.value:
            return body.encode("utf-8"), {"Content-Type": "multipart/form-data"}
        return body.encode("utf-8"), {}

    def _apply_authorization(
        self,
        request: Request,
        headers: dict[str, str],
        params: list[tuple[str, str]],
        variables: dict[str, dict[str, Any]] | None,
        console_logs: list[ConsoleLog] | None = None,
    ) -> tuple[dict[str, str], list[tuple[str, str]]]:
        auth = request.authorization
        if auth is None or auth.type == AuthorizationType.NONE.value:
            return headers, params
        if auth.type == AuthorizationType.BEARER.value:
            if not auth.token:
                raise RequestExecutionError("Bearer token is required.")
            headers["Authorization"] = f"Bearer {self._resolve_nested(auth.token, variables, console_logs)}"
            return headers, params
        if auth.type == AuthorizationType.BASIC.value:
            if not auth.username or not auth.password:
                raise RequestExecutionError("Basic authentication requires username and password.")
            username = self._resolve_nested(auth.username, variables, console_logs)
            password = self._resolve_nested(auth.password, variables, console_logs)
            token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
            return headers, params
        if auth.type == AuthorizationType.API_KEY.value:
            if not auth.api_key_name or not auth.api_key_value or not auth.api_key_in:
                raise RequestExecutionError("API key authentication requires name, value, and location.")
            key = self._resolve_nested(auth.api_key_name, variables, console_logs)
            value = self._resolve_nested(auth.api_key_value, variables, console_logs)
            if auth.api_key_in == "header":
                headers[key] = value
            else:
                params.append((key, value))
            return headers, params
        raise RequestExecutionError("Unsupported authorization configuration.")

    def _build_request(self, request: Request, variables: dict[str, dict[str, Any]] | None, console_logs: list[ConsoleLog] | None = None) -> PreparedRequest:
        url = self._resolve_nested(request.url, variables, console_logs)
        self._validate_url(url)
        if console_logs is not None:
            console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="INFO", message="URL security validation passed"))
        headers = self._serialize_headers(request, variables, console_logs)
        params = self._serialize_query_parameters(request, variables, console_logs)
        headers, params = self._apply_authorization(request, headers, params, variables, console_logs)
        body, body_headers = self._serialize_body(request, variables, console_logs)
        headers.update(body_headers)
        return PreparedRequest(
            method=request.method,
            url=url,
            headers=headers,
            query_params=params,
            content=body,
            timeout=float(request.timeout),
            follow_redirects=request.follow_redirects,
            verify_ssl=request.verify_ssl,
            cookies={},
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            follow_redirects=True,
        )

    def _snapshot_request(self, request: Request, active_env_id: UUID | None) -> str:
        return json.dumps(
            {
                "id": str(request.id),
                "method": request.method,
                "url": request.url,
                "body": request.body,
                "body_type": request.body_type,
                "timeout": request.timeout,
                "follow_redirects": request.follow_redirects,
                "verify_ssl": request.verify_ssl,
                "headers": [{"key": h.key, "value": h.value, "enabled": h.enabled} for h in request.headers],
                "query_parameters": [{"key": q.key, "value": q.value, "enabled": q.enabled} for q in request.query_parameters],
                "authorization": None
                if request.authorization is None
                else {
                    "type": request.authorization.type,
                    "token": request.authorization.token,
                    "username": request.authorization.username,
                    "password": request.authorization.password,
                    "api_key_name": request.authorization.api_key_name,
                    "api_key_value": request.authorization.api_key_value,
                    "api_key_in": request.authorization.api_key_in,
                },
                "environment_id": str(active_env_id) if active_env_id else None,
            }
        )

    def _store_history(
        self,
        user: User,
        request: Request,
        active_env_id: UUID | None,
        duration_ms: float,
        status_code: int | None,
        response_snapshot: dict[str, Any] | None,
        execution_status: str,
        error: str | None,
    ) -> None:
        history = RequestExecutionHistory(
            user_id=user.id,
            request_id=request.id,
            request_snapshot=self._snapshot_request(request, active_env_id),
            response_snapshot=json.dumps(response_snapshot) if response_snapshot is not None else None,
            duration_ms=duration_ms,
            status_code=status_code,
            execution_status=execution_status,
            executed_at=datetime.now(timezone.utc),
            error=error,
        )
        self.repository.create_history(history)

    async def replay(self, user: User, history_id: UUID) -> ExecutionResponse:
        history_item = self.repository.get_history_item(history_id)
        if not history_item or history_item.user_id != user.id:
            raise RequestNotFoundError("History item not found.")
            
        try:
            req_snap = json.loads(history_item.request_snapshot)
        except Exception:
            raise RequestExecutionError("Invalid request snapshot in history.")

        # Reconstruct an in-memory Request object
        request = Request(
            id=UUID(req_snap.get("id")) if req_snap.get("id") else history_item.request_id or uuid.uuid4(),
            user_id=user.id,
            environment_id=UUID(req_snap.get("environment_id")) if req_snap.get("environment_id") else None,
            method=req_snap.get("method", "GET"),
            url=req_snap.get("url", ""),
            body=req_snap.get("body"),
            body_type=req_snap.get("body_type", BodyType.NONE.value),
            timeout=req_snap.get("timeout", 30),
            follow_redirects=req_snap.get("follow_redirects", True),
            verify_ssl=req_snap.get("verify_ssl", True),
        )
        request.headers = [RequestHeader(key=h["key"], value=h["value"], enabled=h.get("enabled", True)) for h in req_snap.get("headers", [])]
        request.query_parameters = [RequestQueryParameter(key=q["key"], value=q["value"], enabled=q.get("enabled", True)) for q in req_snap.get("query_parameters", [])]
        
        auth_snap = req_snap.get("authorization")
        if auth_snap:
            request.authorization = RequestAuthorization(
                type=auth_snap.get("type", AuthorizationType.NONE.value),
                token=auth_snap.get("token"),
                username=auth_snap.get("username"),
                password=auth_snap.get("password"),
                api_key_name=auth_snap.get("api_key_name"),
                api_key_value=auth_snap.get("api_key_value"),
                api_key_in=auth_snap.get("api_key_in"),
            )
            
        return await self._execute_request_obj(user, request)

    async def execute(self, user: User, request_id: UUID) -> ExecutionResponse:
        request = self._load_request(request_id)
        self._verify_owner(request, user.id)
        return await self._execute_request_obj(user, request)
        
    async def _execute_request_obj(self, user: User, request: Request) -> ExecutionResponse:
        active_env = self._get_active_environment(user.id)
        variables = active_env.variables if active_env else None
        
        console_logs: list[ConsoleLog] = []
        started_at = datetime.now(timezone.utc)
        console_logs.append(ConsoleLog(timestamp=started_at, level="REQUEST", message=f"{request.method} {request.url}"))
        
        if active_env:
            console_logs.append(ConsoleLog(timestamp=started_at, level="INFO", message=f"Environment: {active_env.name}"))
        else:
            console_logs.append(ConsoleLog(timestamp=started_at, level="INFO", message="No active environment"))

        status_code: int | None = None
        reason_phrase: str | None = None
        response_headers: dict[str, str] = {}
        response_body: str | None = None
        response_size: int | None = None
        content_type: str | None = None
        cookies: dict[str, str] = {}
        redirect_count = 0
        error_text: str | None = None
        execution_status = "success"
        duration_ms = 0.0
        
        try:
            prepared = self._build_request(request, variables, console_logs)
            console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="REQUEST", message="Request sent"))
        except Exception as exc:
            error_text = str(exc)
            execution_status = "failed"
            # console_logs already appended the error during _build_request
            self._store_history(
                user=user,
                request=request,
                active_env_id=active_env.id if active_env else None,
                duration_ms=0,
                status_code=None,
                response_snapshot={"error": error_text, "timestamp": started_at.isoformat()},
                execution_status=execution_status,
                error=error_text,
            )
            return ExecutionResponse(
                status_code=None,
                reason_phrase=None,
                headers={},
                body=None,
                response_size=None,
                duration_ms=0,
                content_type=None,
                cookies={},
                redirect_count=0,
                timestamp=started_at,
                error=error_text,
                console_logs=console_logs
            )

        loop = asyncio.get_running_loop()
        start_perf = loop.time()
        client = await self._get_client()
        should_close = self._client is None
        
        try:
            response = await client.request(
                prepared.method,
                prepared.url,
                headers=prepared.headers,
                params=prepared.query_params or None,
                content=prepared.content,
                timeout=prepared.timeout,
                follow_redirects=prepared.follow_redirects,
            )
            status_code = response.status_code
            reason_phrase = response.reason_phrase
            response_headers = dict(response.headers)
            content_type = response.headers.get("content-type")
            cookies = dict(response.cookies)
            redirect_count = len(response.history)
            body_bytes = await response.aread()
            response_size = len(body_bytes)
            if response_size > settings.max_response_size:
                raise ResponseTooLargeError("Response too large.")
            response_body = body_bytes.decode(response.encoding or "utf-8", errors="replace")
        except httpx.TimeoutException as exc:
            execution_status = "failed"
            error_text = "Request timed out."
            raise RequestTimeoutError(error_text) from exc
        except httpx.TooManyRedirects as exc:
            execution_status = "failed"
            error_text = "Too many redirects."
            raise RedirectLimitExceededError(error_text) from exc
        except httpx.ConnectError as exc:
            execution_status = "failed"
            error_text = "Connection failed."
            raise ConnectionFailureError(error_text) from exc
        except httpx.ReadTimeout as exc:
            execution_status = "failed"
            error_text = "Request timed out."
            raise RequestTimeoutError(error_text) from exc
        except httpx.UnsupportedProtocol as exc:
            execution_status = "failed"
            error_text = "Invalid URL."
            raise InvalidRequestURLError(error_text) from exc
        except httpx.LocalProtocolError as exc:
            execution_status = "failed"
            error_text = "Invalid request configuration."
            raise RequestExecutionError(error_text) from exc
        except ssl.SSLError as exc:
            execution_status = "failed"
            error_text = "SSL verification failed."
            raise SSLVerificationError(error_text) from exc
        except asyncio.CancelledError as exc:
            execution_status = "failed"
            error_text = "Request cancelled."
            raise RequestCancelledError(error_text) from exc
        except Exception as exc:
            execution_status = "failed"
            error_text = str(exc)
            console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="ERROR", message=error_text))
            raise
        finally:
            duration_ms = (loop.time() - start_perf) * 1000
            if error_text:
                console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="ERROR", message=error_text))
            elif status_code is not None:
                kb = round((response_size or 0) / 1024, 1)
                size_str = f"{kb} KB" if kb >= 1 else f"{response_size} B"
                dur = round(duration_ms)
                msg = f"{status_code} {reason_phrase} · {dur}ms · {size_str}"
                
                safe_url = self._resolve_nested(request.url, variables, mask_secrets=True)
                details = f"Method:\n{prepared.method}\n\nURL:\n{safe_url}\n\nEnvironment:\n{active_env.name if active_env else 'None'}\n\nStatus:\n{status_code} {reason_phrase}\n\nDuration:\n{dur} ms\n\nResponse size:\n{size_str}"
                console_logs.append(ConsoleLog(timestamp=datetime.now(timezone.utc), level="SUCCESS", message=msg, details=details))

            response_snapshot = None
            if status_code is not None:
                response_snapshot = {
                    "status_code": status_code,
                    "reason_phrase": reason_phrase,
                    "headers": response_headers,
                    "body": response_body,
                    "response_size": response_size,
                    "content_type": content_type,
                    "cookies": cookies,
                    "redirect_count": redirect_count,
                    "timestamp": started_at.isoformat(),
                    "error": error_text,
                }
            self._store_history(
                user=user,
                request=request,
                active_env_id=active_env.id if active_env else None,
                duration_ms=duration_ms,
                status_code=status_code,
                response_snapshot=response_snapshot,
                execution_status=execution_status,
                error=error_text,
            )
            if should_close:
                await client.aclose()

        return ExecutionResponse(
            status_code=status_code,
            reason_phrase=reason_phrase,
            headers=response_headers,
            body=response_body,
            response_size=response_size,
            duration_ms=duration_ms,
            content_type=content_type,
            cookies=cookies,
            redirect_count=redirect_count,
            timestamp=started_at,
            error=error_text,
            console_logs=console_logs,
        )

    def execute_sync(self, user: User, request_id: UUID) -> ExecutionResponse:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute(user, request_id))
        raise RuntimeError("execute_sync cannot be called from within a running event loop.")

    def list_history(
        self,
        user: User,
        request_id: UUID,
        search: str | None = None,
        status_code: int | None = None,
        execution_status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RequestExecutionHistory], int]:
        request = self._load_request(request_id)
        self._verify_owner(request, user.id)
        return self.repository.list_history(
            request_id,
            search=search,
            status_code=status_code,
            execution_status=execution_status,
            limit=limit,
            offset=offset,
        )

    def list_global_history(
        self,
        user: User,
        search: str | None = None,
        methods: list[str] | None = None,
        status_classes: list[str] | None = None,
        duration_min: int | None = None,
        duration_max: int | None = None,
        date_min: datetime | None = None,
        collection_id: UUID | None = None,
        environment_id: UUID | None = None,
        execution_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        db_items, total = self.repository.list_global_history(
            user.id,
            search=search,
            methods=methods,
            status_classes=status_classes,
            duration_min=duration_min,
            duration_max=duration_max,
            date_min=date_min,
            collection_id=collection_id,
            environment_id=environment_id,
            execution_status=execution_status,
            limit=limit,
            offset=offset,
        )

        parsed_items = []
        for item in db_items:
            req_snap = {}
            res_snap = {}
            try:
                if item.request_snapshot:
                    req_snap = json.loads(item.request_snapshot)
            except json.JSONDecodeError:
                pass
            
            try:
                if item.response_snapshot:
                    res_snap = json.loads(item.response_snapshot)
            except json.JSONDecodeError:
                pass

            parsed_items.append({
                "id": item.id,
                "request_id": item.request_id,
                "method": req_snap.get("method", "UNKNOWN"),
                "url": req_snap.get("url", "UNKNOWN"),
                "status_code": item.status_code,
                "duration_ms": item.duration_ms,
                "response_size": res_snap.get("response_size"),
                "environment_id": req_snap.get("environment_id"),
                "executed_at": item.executed_at,
                "execution_status": item.execution_status,
            })

        return parsed_items, total

    def get_global_history_item(self, user: User, history_id: UUID) -> dict[str, Any]:
        item = self.repository.get_history_item(history_id)
        if not item or item.user_id != user.id:
            raise RequestNotFoundError("History item not found.")
            
        req_snap = {}
        res_snap = None
        try:
            if item.request_snapshot:
                req_snap = json.loads(item.request_snapshot)
        except json.JSONDecodeError:
            pass
            
        try:
            if item.response_snapshot:
                res_snap = json.loads(item.response_snapshot)
        except json.JSONDecodeError:
            pass
            
        return {
            "id": item.id,
            "request_id": item.request_id,
            "method": req_snap.get("method", "GET"),
            "url": req_snap.get("url", ""),
            "status_code": item.status_code,
            "duration_ms": item.duration_ms,
            "response_size": res_snap.get("response_size") if res_snap else None,
            "environment_id": req_snap.get("environment_id"),
            "executed_at": item.executed_at,
            "execution_status": item.execution_status,
            "request_snapshot": req_snap,
            "response_snapshot": res_snap,
        }
