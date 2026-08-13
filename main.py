import asyncio
import json
import time
import uuid
from copy import deepcopy

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.exceptions import (
    ActiveEnvironmentNotFoundError,
    AuthenticationError,
    EnvironmentAccessDeniedError,
    EnvironmentNotFoundError,
    RequestNotFoundError,
    RequestExecutionError,
    CollectionAccessDeniedError,
    CollectionNotFoundError,
    ExportError,
    ImportLimitExceededError,
    ImportParseError,
    ImportValidationError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    UserAlreadyExistsError,
    UsernameAlreadyExistsError,
)
from app.core.logging import get_logger
from app.routers.collection_router import router as collection_router
from app.routers.ai_router import router as ai_router
from app.routers.import_export_router import router as import_export_router
from app.routers.environment_router import router as environment_router
from app.routers.request_router import router as request_router
from app.routers.user_router import router as auth_router
from app.routers.history_router import router as history_router

settings = get_settings()
logger = get_logger("app")


def build_error_response(code: str, message: str, request_id: str, status_code: int):
    content = {
        "error": {"code": code, "message": message},
        "request_id": request_id,
    }
    return JSONResponse(status_code=status_code, content=content)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def attach_request_id(response: JSONResponse, request_id: str) -> JSONResponse:
    response.headers["X-Request-Id"] = request_id
    return response


def build_success_response(data, request_id: str, message: str = "Request completed successfully.", status_code: int = 200):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data,
            "request_id": request_id,
        },
    )


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


class SuccessEnvelopeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.status_code >= 400 or response.status_code == 204:
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        if not body:
            return response

        try:
            payload = json.loads(body.decode(response.charset or "utf-8"))
        except json.JSONDecodeError:
            return Response(content=body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)

        if isinstance(payload, dict) and {"success", "data", "request_id"} <= set(payload):
            return Response(content=body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)

        request_id = get_request_id(request)
        message = "Request completed successfully."
        if response.status_code == 201:
            message = "Resource created successfully."
        wrapped = build_success_response(payload, request_id, message=message, status_code=response.status_code)
        for key, value in response.headers.items():
            if key.lower() not in {"content-length", "content-type"}:
                wrapped.headers[key] = value
        wrapped.headers["X-Request-Id"] = request_id
        return wrapped
        # Unreachable, but keeps the response contract explicit.


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = get_request_id(request)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        timeout_seconds = settings.request_timeout_seconds
        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            raise HTTPException(status_code=504, detail="Request timed out.") from exc


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                size = 0
            if size > settings.max_request_size:
                raise HTTPException(status_code=413, detail="Request body too large.")

        if request.method in {"POST", "PUT", "PATCH"}:
            if request.headers.get("content-type", "").startswith("multipart/"):
                if request.headers.get("content-length"):
                    try:
                        upload_size = int(request.headers["content-length"])
                    except ValueError:
                        upload_size = settings.max_upload_size + 1
                    if upload_size > settings.max_upload_size:
                        raise HTTPException(status_code=413, detail="Upload too large.")

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        response.headers["Permissions-Policy"] = "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=()"
        return response


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API Studio AI backend. Successful JSON responses are wrapped in a standard envelope: {success, message, data, request_id}.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_host_list(),
)
cors_origins = settings.cors_origin_list()
if settings.environment.lower() == "production" and "*" in cors_origins:
    raise ValueError("Wildcard CORS origins are not allowed in production.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTimeoutMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SuccessEnvelopeMiddleware)
app.add_middleware(RequestIDMiddleware)
app.include_router(auth_router)
app.include_router(environment_router)
app.include_router(collection_router)
app.include_router(request_router)
app.include_router(history_router)
app.include_router(import_export_router)
app.include_router(ai_router)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", include_in_schema=False)
def frontend_home():
    return FileResponse("frontend/index.html")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("schemas", {})
    schema["components"]["schemas"]["SuccessEnvelope"] = {
        "title": "SuccessEnvelope",
        "type": "object",
        "required": ["success", "message", "data", "request_id"],
        "properties": {
            "success": {"type": "boolean", "example": True},
            "message": {"type": "string", "example": "Request completed successfully."},
            "data": {},
            "request_id": {"type": "string", "format": "uuid"},
        },
        "description": "Standard envelope for successful JSON responses.",
    }
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            for status_code, response in responses.items():
                if status_code == "204":
                    continue
                content = response.get("content", {})
                json_content = content.get("application/json")
                if not json_content:
                    continue
                original_schema = deepcopy(json_content.get("schema", {}))
                if isinstance(original_schema, dict) and original_schema.get("title") == "SuccessEnvelope":
                    continue
                json_content["schema"] = {
                    "allOf": [
                        {"$ref": "#/components/schemas/SuccessEnvelope"},
                        {
                            "type": "object",
                            "properties": {
                                "data": original_schema or {},
                            },
                        },
                    ]
                }
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = get_request_id(request)
    response = JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": "Request validation failed.", "fields": [{"field": ".".join(str(part) for part in error.get("loc", []) if part != "body"), "message": error.get("msg", "Invalid value.")} for error in exc.errors()]}, "request_id": request_id})
    return attach_request_id(response, request_id)


@app.exception_handler(UserAlreadyExistsError)
async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("user_already_exists", str(exc), request_id, 409), request_id)


@app.exception_handler(UsernameAlreadyExistsError)
async def username_already_exists_handler(request: Request, exc: UsernameAlreadyExistsError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("username_already_exists", str(exc), request_id, 409), request_id)


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("invalid_credentials", str(exc), request_id, 401), request_id)


@app.exception_handler(TokenExpiredError)
async def token_expired_handler(request: Request, exc: TokenExpiredError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("token_expired", str(exc), request_id, 401), request_id)


@app.exception_handler(InvalidTokenError)
async def invalid_token_handler(request: Request, exc: InvalidTokenError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("invalid_token", str(exc), request_id, 401), request_id)


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("authentication_error", str(exc), request_id, 401), request_id)


@app.exception_handler(InactiveUserError)
async def inactive_user_handler(request: Request, exc: InactiveUserError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("inactive_user", str(exc), request_id, 403), request_id)


@app.exception_handler(EnvironmentNotFoundError)
async def environment_not_found_handler(request: Request, exc: EnvironmentNotFoundError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("environment_not_found", str(exc), request_id, 404), request_id)


@app.exception_handler(EnvironmentAccessDeniedError)
async def environment_access_denied_handler(request: Request, exc: EnvironmentAccessDeniedError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("environment_access_denied", str(exc), request_id, 403), request_id)


@app.exception_handler(ActiveEnvironmentNotFoundError)
async def active_environment_not_found_handler(request: Request, exc: ActiveEnvironmentNotFoundError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("active_environment_not_found", str(exc), request_id, 404), request_id)


@app.exception_handler(RequestNotFoundError)
async def request_not_found_handler(request: Request, exc: RequestNotFoundError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("request_not_found", str(exc), request_id, 404), request_id)


@app.exception_handler(RequestExecutionError)
async def request_execution_error_handler(request: Request, exc: RequestExecutionError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("request_execution_error", str(exc), request_id, 400), request_id)


@app.exception_handler(CollectionNotFoundError)
async def collection_not_found_handler(request: Request, exc: CollectionNotFoundError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("collection_not_found", str(exc), request_id, 404), request_id)


@app.exception_handler(CollectionAccessDeniedError)
async def collection_access_denied_handler(request: Request, exc: CollectionAccessDeniedError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("collection_access_denied", str(exc), request_id, 403), request_id)


@app.exception_handler(ImportValidationError)
async def import_validation_handler(request: Request, exc: ImportValidationError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("import_validation_error", str(exc), request_id, 400), request_id)


@app.exception_handler(ImportParseError)
async def import_parse_handler(request: Request, exc: ImportParseError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("import_parse_error", str(exc), request_id, 400), request_id)


@app.exception_handler(ImportLimitExceededError)
async def import_limit_handler(request: Request, exc: ImportLimitExceededError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("import_limit_exceeded", str(exc), request_id, 413), request_id)


@app.exception_handler(ExportError)
async def export_error_handler(request: Request, exc: ExportError):
    request_id = get_request_id(request)
    return attach_request_id(build_error_response("export_error", str(exc), request_id, 400), request_id)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    request_id = get_request_id(request)
    logger.exception("database_error", extra={"request_id": request_id, "path": request.url.path})
    return attach_request_id(
        build_error_response("database_error", "Database operation failed.", request_id, 500),
        request_id,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = get_request_id(request)
    code = "http_error"
    if exc.status_code == 413:
        code = "request_too_large"
    elif exc.status_code == 404:
        code = "not_found"
    elif exc.status_code == 504:
        code = "request_timeout"
    return attach_request_id(build_error_response(code, str(exc.detail), request_id, exc.status_code), request_id)


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    request_id = get_request_id(request)
    logger.exception("unexpected_error", extra={"request_id": request_id, "path": request.url.path})
    return attach_request_id(
        build_error_response("internal_server_error", "An unexpected error occurred.", request_id, 500),
        request_id,
    )


@app.get("/health")
def health_check(request: Request) -> dict[str, str]:
    return build_success_response({"status": "ok"}, request_id=get_request_id(request), message="Healthy.", status_code=200)


@app.get("/ready")
def readiness_check(request: Request) -> dict[str, str]:
    return build_success_response({"status": "ready"}, request_id=get_request_id(request), message="Ready.", status_code=200)
