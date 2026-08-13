import importlib
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_import_export.db")
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
    import app.services.import_export_service as import_export_service_module
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
    importlib.reload(import_export_service_module)
    main_module = importlib.reload(main_module)
    database_module.Base.metadata.create_all(bind=database_module.engine)

    return TestClient(main_module.app)


def auth_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    email = f"ie_{suffix}@example.com"
    username = f"ie_{suffix}"
    client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": "StrongPass1!"})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPass1!"}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_import_postman_and_export_postman(client):
    headers = auth_headers(client)
    postman = {
        "info": {"name": "Imported", "description": "Example", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "item": [
            {
                "name": "Get users",
                "request": {
                    "method": "GET",
                    "header": [{"key": "Accept", "value": "application/json"}],
                    "url": {"raw": "https://example.com/users?limit=10", "query": [{"key": "limit", "value": "10"}]},
                },
            }
        ],
    }
    imported = client.post("/api/v1/import/postman", json={"content": json.dumps(postman)}, headers=headers)
    assert imported.status_code == 201
    summary = imported.json()["data"]
    assert summary["collections_created"] == 1
    assert summary["requests_created"] == 1

    collection_id = summary["collection_id"]
    exported = client.get(f"/api/v1/export/postman/{collection_id}", headers=headers)
    assert exported.status_code == 200
    payload = json.loads(exported.json()["data"]["content"])
    assert payload["info"]["name"] == "Imported"
    assert payload["item"][0]["name"] == "Get users"


def test_import_openapi_and_export_openapi(client):
    headers = auth_headers(client)
    openapi = """
openapi: 3.0.3
info:
  title: Pets API
  version: 1.0.0
paths:
  /pets:
    get:
      summary: List pets
      description: Returns pets
      responses:
        '200':
          description: ok
"""
    imported = client.post("/api/v1/import/openapi", json={"content": openapi}, headers=headers)
    assert imported.status_code == 201
    collection_id = imported.json()["data"]["collection_id"]
    exported = client.get(f"/api/v1/export/openapi/{collection_id}", headers=headers)
    assert exported.status_code == 200
    payload = json.loads(exported.json()["data"]["content"])
    assert payload["openapi"] == "3.0.3"
    assert "/pets" in payload["paths"]


def test_import_curl_and_export_curl(client):
    headers = auth_headers(client)
    curl = "curl 'https://example.com/users?page=1' -X POST -H 'Authorization: Bearer token123' -H 'Accept: application/json' --data-raw '{\"name\":\"alice\"}'"
    imported = client.post("/api/v1/import/curl", json={"content": curl}, headers=headers)
    assert imported.status_code == 201
    assert imported.json()["data"]["requests_created"] == 1

    request_id = client.get("/api/v1/requests", headers=headers).json()["data"][0]["id"]
    exported = client.get(f"/api/v1/export/curl/{request_id}", headers=headers)
    assert exported.status_code == 200
    assert "curl" in exported.json()["data"]["content"]
    assert "Authorization: Bearer token123" in exported.json()["data"]["content"]


def test_malformed_import_is_rejected(client):
    headers = auth_headers(client)
    response = client.post("/api/v1/import/openapi", json={"content": "not: [valid"}, headers=headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] in {"import_parse_error", "import_validation_error"}
