import importlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import EnvironmentAccessDeniedError, EnvironmentNotFoundError, RequestNotFoundError
from app.schemas.environment import EnvironmentCreate
from app.schemas.request import RequestAuthorizationBase, RequestCreate, RequestHeaderBase, RequestQueryParameterBase, RequestUpdate
from app.schemas.user import UserCreate
from app.services.environment_service import EnvironmentService
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


def _make_user(service: UserService, email: str = "alice@example.com", username: str = "alice_01"):
    return service.register(UserCreate(email=email, username=username, password="StrongPass1!"))


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_request.db")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("REFRESH_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    monkeypatch.setenv("TRUSTED_HOSTS", "testserver,localhost,127.0.0.1,[::1]")
    monkeypatch.setenv("MAX_REQUEST_SIZE", "1048576")
    monkeypatch.setenv("MAX_UPLOAD_SIZE", "1048576")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "5")

    import app.core.config as config_module
    import app.core.database as database_module
    import app.models.collection as collection_model_module
    import app.models.environment as environment_model_module
    import app.models.request as request_model_module
    import app.models.user as user_model_module
    import app.core.security as security_module
    import app.dependencies as dependencies_module
    import app.services.user_service as user_service_module
    import app.services.environment_service as environment_service_module
    import app.services.request_service as request_service_module
    import main as main_module

    importlib.reload(config_module)
    importlib.reload(database_module)
    importlib.reload(user_model_module)
    importlib.reload(collection_model_module)
    importlib.reload(environment_model_module)
    importlib.reload(request_model_module)
    importlib.reload(security_module)
    importlib.reload(dependencies_module)
    importlib.reload(user_service_module)
    importlib.reload(environment_service_module)
    importlib.reload(request_service_module)
    main_module = importlib.reload(main_module)
    database_module.Base.metadata.create_all(bind=database_module.engine)

    return TestClient(main_module.app)


def _auth_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    email = f"alice_{suffix}@example.com"
    username = f"alice_{suffix}"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": "StrongPass1!"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass1!"},
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def test_request_crud_and_relationships(db_session):
    user_service = UserService(db_session)
    env_service = EnvironmentService(db_session)
    request_service = RequestService(db_session)
    user = _make_user(user_service)
    environment = env_service.create(user, EnvironmentCreate(name="Local", variables={"BASE_URL": {"value": "https://api.example.com", "secret": False}}, is_active=True))

    created = request_service.create(
        user,
        RequestCreate(
            name="List users",
            description="GET users",
            method="GET",
            url="https://api.example.com/users",
            body=None,
            body_type="none",
            timeout=30,
            follow_redirects=True,
            verify_ssl=True,
            is_favorite=True,
            environment_id=environment.id,
            headers=[RequestHeaderBase(key="Accept", value="application/json", enabled=True)],
            query_parameters=[RequestQueryParameterBase(key="page", value="1", enabled=True)],
            authorization=RequestAuthorizationBase(type="bearer", token="secret-token"),
        ),
    )

    assert created.name == "List users"
    assert created.headers[0].key == "Accept"
    assert created.query_parameters[0].key == "page"
    assert created.authorization.type == "bearer"

    listed = request_service.list(user)
    assert len(listed) == 1

    fetched = request_service.get(user, created.id)
    assert fetched.url == "https://api.example.com/users"

    updated = request_service.update(user, created.id, RequestUpdate(name="List active users", is_favorite=False))
    assert updated.name == "List active users"
    assert updated.is_favorite is False

    request_service.delete(user, created.id)
    with pytest.raises(RequestNotFoundError):
        request_service.get(user, created.id)


def test_request_ownership_and_environment_validation(db_session):
    user_service = UserService(db_session)
    env_service = EnvironmentService(db_session)
    request_service = RequestService(db_session)
    owner = _make_user(user_service, email="owner@example.com", username="owner")
    other = _make_user(user_service, email="other@example.com", username="other")
    environment = env_service.create(owner, EnvironmentCreate(name="Private", variables={}))
    created = request_service.create(
        owner,
        RequestCreate(
            name="Private call",
            method="GET",
            url="https://example.com",
            body_type="none",
            environment_id=environment.id,
        ),
    )

    with pytest.raises(EnvironmentAccessDeniedError):
        request_service.get(other, created.id)

    with pytest.raises(EnvironmentAccessDeniedError):
        request_service.create(
            other,
            RequestCreate(name="Bad env", method="GET", url="https://example.com", body_type="none", environment_id=environment.id),
        )

    with pytest.raises(EnvironmentNotFoundError):
        request_service.create(
            owner,
            RequestCreate(name="Missing env", method="GET", url="https://example.com", body_type="none", environment_id=uuid4()),
        )


def test_request_endpoints_and_validation(client):
    headers = _auth_headers(client)

    bad_method = client.post(
        "/api/v1/requests",
        json={"name": "Bad", "method": "TRACE", "url": "https://example.com", "body_type": "none"},
        headers=headers,
    )
    assert bad_method.status_code == 422

    created = client.post(
        "/api/v1/requests",
        json={
            "name": "Get users",
            "description": "List users",
            "method": "GET",
            "url": "https://example.com/users",
            "body_type": "none",
            "timeout": 30,
            "follow_redirects": True,
            "verify_ssl": True,
            "is_favorite": False,
            "headers": [{"key": "Accept", "value": "application/json", "enabled": True}],
            "query_parameters": [{"key": "page", "value": "1", "enabled": True}],
            "authorization": {"type": "basic", "username": "user", "password": "pass"},
        },
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()["data"]
    assert body["headers"][0]["key"] == "Accept"
    assert body["query_parameters"][0]["key"] == "page"
    assert body["authorization"]["type"] == "basic"

    request_id = body["id"]
    fetched = client.get(f"/api/v1/requests/{request_id}", headers=headers)
    assert fetched.status_code == 200

    updated = client.patch(f"/api/v1/requests/{request_id}", json={"name": "Get active users"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "Get active users"

    deleted = client.delete(f"/api/v1/requests/{request_id}", headers=headers)
    assert deleted.status_code == 204
