import importlib
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.schemas.request import ExecutionResponse


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_history.db")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("REFRESH_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    monkeypatch.setenv("TRUSTED_HOSTS", "testserver,localhost,127.0.0.1,[::1]")
    monkeypatch.setenv("MAX_REQUEST_SIZE", "1048576")
    monkeypatch.setenv("MAX_UPLOAD_SIZE", "1048576")
    monkeypatch.setenv("MAX_RESPONSE_SIZE", "1048576")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("MAX_REDIRECTS", "5")

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
    import app.services.collection_service as collection_service_module
    import app.services.execution_service as execution_service_module
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
    importlib.reload(collection_service_module)
    importlib.reload(execution_service_module)
    main_module = importlib.reload(main_module)
    database_module.Base.metadata.create_all(bind=database_module.engine)

    return TestClient(main_module.app)


def auth_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    email = f"alice_{suffix}@example.com"
    username = f"alice_{suffix}"
    register = client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": "StrongPass1!"})
    assert register.status_code in {201, 409}
    token = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPass1!"}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_collection_crud_favorites_and_tags(client):
    headers = auth_headers(client)
    created = client.post(
        "/api/v1/collections",
        json={"name": "API Tests", "description": "Main", "is_favorite": False, "tags": ["prod", "api", "prod"]},
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()["data"]
    assert body["name"] == "API Tests"
    assert [tag["name"] for tag in body["tags"]] == ["prod", "api"]

    listing = client.get("/api/v1/collections", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()["data"]) == 1

    collection_id = body["id"]
    updated = client.patch(f"/api/v1/collections/{collection_id}", json={"is_favorite": True, "tags": ["team"]}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["data"]["is_favorite"] is True
    assert [tag["name"] for tag in updated.json()["data"]["tags"]] == ["team"]

    favorited = client.post(f"/api/v1/collections/{collection_id}/favorite", headers=headers)
    assert favorited.status_code == 200
    assert favorited.json()["data"]["is_favorite"] is True

    unfavorited = client.delete(f"/api/v1/collections/{collection_id}/favorite", headers=headers)
    assert unfavorited.status_code == 200
    assert unfavorited.json()["data"]["is_favorite"] is False


def test_history_search_filters_and_pagination(client, monkeypatch):
    headers = auth_headers(client)
    request = client.post(
        "/api/v1/requests",
        json={"name": "Exec", "method": "GET", "url": "https://example.com", "body_type": "none"},
        headers=headers,
    ).json()["data"]
    request_id = request["id"]

    async def fake_execute(self, user, request_id):
        self._store_history(
            user=user,
            request=self._load_request(request_id),
            duration_ms=12.5,
            status_code=200,
            response_snapshot={"status_code": 200, "body": "ok"},
            execution_status="success",
            error=None,
        )
        return ExecutionResponse(
            status_code=200,
            reason_phrase="OK",
            headers={"content-type": "application/json"},
            body="ok",
            response_size=2,
            duration_ms=12.5,
            content_type="application/json",
            cookies={},
            redirect_count=0,
            timestamp=datetime.now(timezone.utc),
            error=None,
        )

    import app.routers.request_router as request_router_module
    import app.services.execution_service as execution_service_module
    monkeypatch.setattr(execution_service_module.ExecutionService, "execute", fake_execute, raising=True)
    monkeypatch.setattr(request_router_module.ExecutionService, "execute", fake_execute, raising=True)

    for _ in range(3):
        client.post(f"/api/v1/requests/{request_id}/execute", headers=headers)

    history = client.get(f"/api/v1/requests/{request_id}/history", headers=headers)
    assert history.status_code == 200
    payload = history.json()["data"]
    assert payload["total"] == 3
    assert len(payload["items"]) == 3

    paged = client.get(f"/api/v1/requests/{request_id}/history?limit=2&offset=1", headers=headers)
    assert paged.status_code == 200
    assert len(paged.json()["data"]["items"]) == 2
