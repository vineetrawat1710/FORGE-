import importlib
import asyncio
import socket
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import InvalidRequestURLError, RequestTimeoutError, ResponseTooLargeError
from app.schemas.environment import EnvironmentCreate
from app.schemas.request import RequestAuthorizationBase, RequestCreate, RequestHeaderBase, RequestQueryParameterBase
from app.schemas.user import UserCreate
from app.services.environment_service import EnvironmentService
from app.services.execution_service import ExecutionService
from app.services.request_service import RequestService
from app.services.user_service import UserService


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    import app.core.database as database_module
    import app.models.collection as collection_model_module
    import app.models.environment as environment_model_module
    import app.models.request as request_model_module
    import app.models.user as user_model_module

    importlib.reload(database_module)
    importlib.reload(user_model_module)
    importlib.reload(collection_model_module)
    importlib.reload(environment_model_module)
    importlib.reload(request_model_module)

    database_module.Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def dns_stub(monkeypatch):
    def fake_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host == "example.com":
            return [
                (socket.AF_INET, socket.SOCK_STREAM, proto, "", ("93.184.216.34", port or 443)),
            ]
        raise socket.gaierror(socket.EAI_NONAME, "name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def _make_user(service: UserService, email: str = "alice@example.com", username: str = "alice_01"):
    return service.register(UserCreate(email=email, username=username, password="StrongPass1!"))


def _make_request(db_session, *, body: str | None = None, body_type: str = "none", authorization: RequestAuthorizationBase | None = None):
    user_service = UserService(db_session)
    env_service = EnvironmentService(db_session)
    request_service = RequestService(db_session)
    user = _make_user(user_service)
    environment = env_service.create(
        user,
        EnvironmentCreate(
            name="Local",
            variables={
                "BASE_URL": {"value": "https://example.com", "secret": False},
                "TOKEN": {"value": "env-token", "secret": True},
            },
            is_active=True,
        ),
    )
    created = request_service.create(
        user,
        RequestCreate(
            name="Exec request",
            method="POST",
            url="{{BASE_URL}}/users?existing=1",
            body=body,
            body_type=body_type,
            timeout=30,
            follow_redirects=True,
            verify_ssl=True,
            environment_id=environment.id,
            headers=[RequestHeaderBase(key="X-Token", value="{{TOKEN}}", enabled=True)],
            query_parameters=[RequestQueryParameterBase(key="page", value="2", enabled=True)],
            authorization=authorization or RequestAuthorizationBase(type="bearer", token="{{TOKEN}}"),
        ),
    )
    return user, created


@pytest.mark.asyncio
async def test_execute_request_pipeline_and_history(db_session):
    user, created = _make_request(db_session, body='{"hello":"{{TOKEN}}"}', body_type="json")
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content.decode()
        return httpx.Response(200, headers={"content-type": "application/json"}, text='{"ok":true}', request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.com")
    service = ExecutionService(db_session, client=client)

    result = await service.execute(user, created.id)

    assert result.status_code == 200
    assert result.body == '{"ok":true}'
    assert "https://example.com/users" in captured["url"]
    assert parse_qs(urlparse(captured["url"]).query)["page"] == ["2"]
    assert captured["headers"]["authorization"] == "Bearer env-token"
    assert captured["headers"]["x-token"] == "env-token"

    history, total = service.list_history(user, created.id)
    assert total == 1
    assert len(history) == 1
    assert history[0].status_code == 200
    assert history[0].request_snapshot

    await client.aclose()


@pytest.mark.asyncio
async def test_execute_request_timeout_and_invalid_protocol(db_session):
    user, created = _make_request(db_session)

    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler), base_url="https://example.com")
    service = ExecutionService(db_session, client=client)

    with pytest.raises(RequestTimeoutError):
        await service.execute(user, created.id)

    stored = service.repository.get_by_id(created.id)
    assert stored is not None
    stored.url = "file:///etc/passwd"
    db_session.commit()
    with pytest.raises(InvalidRequestURLError):
        await service.execute(user, created.id)

    await client.aclose()


@pytest.mark.asyncio
async def test_execute_response_size_limit(db_session, monkeypatch):
    user, created = _make_request(db_session)

    async def large_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="x" * 2048, request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(large_handler), base_url="https://example.com")
    service = ExecutionService(db_session, client=client)
    import app.services.execution_service as execution_service_module

    monkeypatch.setattr(execution_service_module.settings, "max_response_size", 10, raising=False)

    with pytest.raises(ResponseTooLargeError):
        await service.execute(user, created.id)
    await client.aclose()
