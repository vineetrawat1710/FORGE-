import importlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.exceptions import ActiveEnvironmentNotFoundError, EnvironmentAccessDeniedError, EnvironmentNotFoundError
from app.schemas.environment import EnvironmentCreate, EnvironmentUpdate
from app.schemas.user import UserCreate
from app.services.environment_service import EnvironmentService
from app.services.user_service import UserService


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


def _make_user(service: UserService, email: str = "alice@example.com", username: str = "alice_01"):
    return service.register(UserCreate(email=email, username=username, password="StrongPass1!"))


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_env.db")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("REFRESH_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    monkeypatch.setenv("TRUSTED_HOSTS", "testserver,localhost,127.0.0.1,[::1]")
    monkeypatch.setenv("MAX_REQUEST_SIZE", "1048576")
    monkeypatch.setenv("MAX_UPLOAD_SIZE", "1048576")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "5")

    import app.core.config as config_module
    import app.core.database as database_module
    import app.models.environment as environment_model_module
    import app.models.user as user_model_module
    import app.core.security as security_module
    import app.dependencies as dependencies_module
    import app.services.user_service as user_service_module
    import app.services.environment_service as environment_service_module
    import main as main_module

    importlib.reload(config_module)
    importlib.reload(database_module)
    importlib.reload(user_model_module)
    importlib.reload(environment_model_module)
    importlib.reload(security_module)
    importlib.reload(dependencies_module)
    importlib.reload(user_service_module)
    importlib.reload(environment_service_module)
    main_module = importlib.reload(main_module)
    database_module.Base.metadata.create_all(bind=database_module.engine)

    return TestClient(main_module.app)


def _auth_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    email = f"alice_{suffix}@example.com"
    username = f"alice_{suffix}"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "StrongPass1!",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "StrongPass1!",
        },
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def test_environment_crud_and_activation(db_session):
    user_service = UserService(db_session)
    environment_service = EnvironmentService(db_session)
    user = _make_user(user_service)

    created = environment_service.create(
        user,
        EnvironmentCreate(
            name="Local",
            description="Local development",
            variables={
                "BASE_URL": {"value": "http://localhost:8000", "secret": False},
                "API_KEY": {"value": "super-secret", "secret": True},
            },
            is_active=False,
        ),
    )

    assert created.name == "Local"
    assert created.variables["API_KEY"]["value"] == "****"

    listed = environment_service.list(user)
    assert len(listed) == 1
    assert listed[0].name == "Local"

    fetched = environment_service.get(user, created.id)
    assert fetched.description == "Local development"
    assert fetched.variables["BASE_URL"]["value"] == "http://localhost:8000"

    updated = environment_service.update(
        user,
        created.id,
        EnvironmentUpdate(
            description="Updated",
            variables={"BASE_URL": {"value": "https://example.com", "secret": False}},
        ),
    )
    assert updated.description == "Updated"

    active = environment_service.activate(user, created.id)
    assert active.is_active is True

    resolved = environment_service.resolve_variables("Call {{BASE_URL}}", user.id)
    assert resolved == "Call https://example.com"

    environment_service.delete(user, created.id)
    with pytest.raises(EnvironmentNotFoundError):
        environment_service.get(user, created.id)


def test_environment_ownership_is_enforced(db_session):
    user_service = UserService(db_session)
    environment_service = EnvironmentService(db_session)
    owner = _make_user(user_service, email="owner@example.com", username="owner")
    other = _make_user(user_service, email="other@example.com", username="other")

    created = environment_service.create(
        owner,
        EnvironmentCreate(
            name="Private",
            variables={"BASE_URL": {"value": "https://owner.example", "secret": False}},
        ),
    )

    with pytest.raises(EnvironmentAccessDeniedError):
        environment_service.get(other, created.id)

    with pytest.raises(EnvironmentAccessDeniedError):
        environment_service.update(other, created.id, EnvironmentUpdate(description="nope"))

    with pytest.raises(EnvironmentAccessDeniedError):
        environment_service.delete(other, created.id)


def test_active_environment_lookup_and_masking(db_session):
    user_service = UserService(db_session)
    environment_service = EnvironmentService(db_session)
    user = _make_user(user_service)

    with pytest.raises(ActiveEnvironmentNotFoundError):
        environment_service.get_active_environment(user.id)

    created = environment_service.create(
        user,
        EnvironmentCreate(
            name="Prod",
            variables={"TOKEN": {"value": "secret-token", "secret": True}},
            is_active=True,
        ),
    )

    active = environment_service.get_active_environment(user.id)
    assert active.id == created.id
    assert created.variables["TOKEN"]["value"] == "****"


def test_environment_endpoints(client):
    headers = _auth_headers(client)

    created = client.post(
        "/api/v1/environments",
        json={
            "name": "Local",
            "description": "Local development",
            "variables": {
                "BASE_URL": {"value": "http://localhost:8000", "secret": False},
                "API_KEY": {"value": "super-secret", "secret": True},
            },
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["data"]["variables"]["API_KEY"]["value"] == "****"

    listing = client.get("/api/v1/environments", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    environment_id = created.json()["data"]["id"]
    fetched = client.get(f"/api/v1/environments/{environment_id}", headers=headers)
    assert fetched.status_code == 200

    activated = client.post(f"/api/v1/environments/{environment_id}/activate", headers=headers)
    assert activated.status_code == 200
    assert activated.json()["data"]["is_active"] is True

    updated = client.patch(
        f"/api/v1/environments/{environment_id}",
        json={"description": "Updated"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["description"] == "Updated"

    deleted = client.delete(f"/api/v1/environments/{environment_id}", headers=headers)
    assert deleted.status_code == 204
