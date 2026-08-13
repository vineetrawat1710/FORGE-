import importlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_ai.db")
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
    import app.services.ai_service as ai_service_module
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
    importlib.reload(ai_service_module)
    main_module = importlib.reload(main_module)
    database_module.Base.metadata.create_all(bind=database_module.engine)

    return TestClient(main_module.app)


def auth_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    email = f"ai_{suffix}@example.com"
    username = f"ai_{suffix}"
    client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": "StrongPass1!"})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPass1!"}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_generate_request_and_chat(client):
    headers = auth_headers(client)
    response = client.post("/api/v1/ai/generate-request", json={"prompt": "Create a login request"}, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["request"]["method"] == "POST"
    assert "login" in data["request"]["url"]

    chat = client.post("/api/v1/ai/chat", json={"message": "Create login request"}, headers=headers)
    assert chat.status_code == 200
    assert chat.json()["data"]["tools"]


def test_ai_search_and_explain(client):
    headers = auth_headers(client)
    search = client.post("/api/v1/ai/search", json={"query": "missing"}, headers=headers)
    assert search.status_code == 200
    assert search.json()["data"]["requests"] == []

    explanation = client.post("/api/v1/ai/explain-response", json={"status_code": 401, "headers": {}, "body": "unauthorized"}, headers=headers)
    assert explanation.status_code == 200
    assert "401" not in explanation.json()["data"]["reply"]

