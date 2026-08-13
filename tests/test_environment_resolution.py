import importlib
import asyncio
import socket
import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import RequestExecutionError
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


def _setup_env_and_req(db_session, url="{{base_url}}/users/{{user_id}}?page={{page}}"):
    user_service = UserService(db_session)
    env_service = EnvironmentService(db_session)
    request_service = RequestService(db_session)
    
    user = user_service.register(UserCreate(email="test@example.com", username="test", password="Password1!"))
    
    env = env_service.create(user, EnvironmentCreate(
        name="TestEnv",
        is_active=True,
        variables={
            "base_url": {"value": "https://example.com", "enabled": True, "secret": False},
            "user_id": {"value": "42", "enabled": True, "secret": False},
            "page": {"value": "2", "enabled": True, "secret": False},
            "token": {"value": "secret123", "enabled": True, "secret": True},
            "disabled_var": {"value": "disabled", "enabled": False, "secret": False},
            "recursive1": {"value": "{{recursive2}}", "enabled": True, "secret": False},
            "recursive2": {"value": "{{recursive1}}", "enabled": True, "secret": False},
        }
    ))
    
    req = request_service.create(user, RequestCreate(
        name="TestReq",
        method="GET",
        url=url,
        headers=[RequestHeaderBase(key="Authorization", value="Bearer {{token}}", enabled=True)],
        query_parameters=[],
    ))
    
    return user, env, req, env_service, request_service


@pytest.mark.asyncio
async def test_resolution_success(db_session):
    user, env, req, env_service, req_service = _setup_env_and_req(db_session)
    captured_request = None
    
    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json={"status": "ok"}, request=request)
        
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    exec_service = ExecutionService(db_session, client=client)
    
    await exec_service.execute(user, req.id)
    
    assert str(captured_request.url) == "https://example.com/users/42?page=2"
    assert captured_request.headers.get("Authorization") == "Bearer secret123"
    
    # Verify history snapshot did not leak secret
    history, _ = exec_service.list_history(user, req.id)
    assert len(history) == 1
    assert "Bearer {{token}}" in history[0].request_snapshot
    assert "secret123" not in history[0].request_snapshot

@pytest.mark.asyncio
async def test_resolution_missing_variable(db_session):
    user, env, req, env_service, req_service = _setup_env_and_req(db_session, url="{{missing_var}}")
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    exec_service = ExecutionService(db_session, client=client)
    
    with pytest.raises(RequestExecutionError, match="Variable 'missing_var' was not found in the active environment"):
        await exec_service.execute(user, req.id)

@pytest.mark.asyncio
async def test_resolution_disabled_variable(db_session):
    user, env, req, env_service, req_service = _setup_env_and_req(db_session, url="{{disabled_var}}")
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    exec_service = ExecutionService(db_session, client=client)
    
    with pytest.raises(RequestExecutionError, match="Variable 'disabled_var' is disabled in the active environment"):
        await exec_service.execute(user, req.id)

@pytest.mark.asyncio
async def test_resolution_no_active_environment(db_session):
    user, env, req, env_service, req_service = _setup_env_and_req(db_session)
    
    # Deactivate environment
    env_service.repository.unset_active_for_user(user.id)
    
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    exec_service = ExecutionService(db_session, client=client)
    
    with pytest.raises(RequestExecutionError, match="Variable 'base_url' cannot be resolved because no environment is active"):
        await exec_service.execute(user, req.id)

@pytest.mark.asyncio
async def test_resolution_circular_reference(db_session):
    user, env, req, env_service, req_service = _setup_env_and_req(db_session, url="{{recursive1}}")
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    exec_service = ExecutionService(db_session, client=client)
    
    with pytest.raises(RequestExecutionError, match="Circular reference detected in environment variables"):
        await exec_service.execute(user, req.id)
