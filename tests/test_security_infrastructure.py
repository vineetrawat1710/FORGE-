import importlib
import io
import logging

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_security.db")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("REFRESH_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
    monkeypatch.setenv("TRUSTED_HOSTS", "testserver,localhost,127.0.0.1,[::1]")
    monkeypatch.setenv("MAX_REQUEST_SIZE", "1048576")
    monkeypatch.setenv("MAX_UPLOAD_SIZE", "1048576")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "5")

    import app.core.config as config_module
    import app.core.database as database_module
    import app.models.user as user_model_module
    import app.core.security as security_module
    import app.dependencies as dependencies_module
    import app.services.user_service as user_service_module
    import main as main_module

    importlib.reload(config_module)
    importlib.reload(database_module)
    importlib.reload(user_model_module)
    importlib.reload(security_module)
    importlib.reload(dependencies_module)
    importlib.reload(user_service_module)
    main_module = importlib.reload(main_module)
    database_module.Base.metadata.create_all(bind=database_module.engine)

    yield TestClient(main_module.app)


def test_health_and_ready_endpoints(client):
    health = client.get("/health")
    ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json()["success"] is True
    assert health.json()["data"]["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json()["success"] is True
    assert ready.json()["data"]["status"] == "ready"


def test_security_headers_and_request_id_are_present(client):
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in response.headers
    assert "Permissions-Policy" in response.headers
    assert "X-Request-Id" in response.headers


def test_cors_configuration_restricts_origin(client):
    allowed = client.get("/health", headers={"Origin": "http://localhost:3000"})
    blocked = client.get("/health", headers={"Origin": "https://evil.example"})

    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert blocked.headers.get("access-control-allow-origin") is None


def test_cors_configuration_accepts_all_local_origins(client):
    for origin in [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]:
        response = client.get("/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin


def test_trusted_host_header_rejects_untrusted_host(client):
    response = client.get("/health", headers={"Host": "evil.example"})

    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None


def test_validation_errors_use_consistent_format(client):
    response = client.post("/api/v1/auth/login", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "message" in body["error"]
    assert "request_id" in body
    assert response.headers["X-Request-Id"] == body["request_id"]


def test_business_errors_use_consistent_error_format(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "username": "duplicate_user",
            "password": "StrongPass1!",
        },
    )
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "username": "duplicate_user_2",
            "password": "StrongPass1!",
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] in {"user_already_exists", "username_already_exists"}
    assert "request_id" in body


def test_invalid_cors_configuration_rejects_malformed_origin():
    from app.core.config import Settings

    with pytest.raises(ValueError, match=r"Invalid origin 'invalid-origin'"):
        Settings(
            app_name="API Studio AI Backend",
            environment="development",
            database_url="sqlite:///./test.db",
            secret_key="x" * 32,
            refresh_secret_key="y" * 32,
            cors_origins="invalid-origin",
            trusted_hosts="localhost,127.0.0.1,[::1]",
            max_request_size=1048576,
            max_upload_size=1048576,
            max_response_size=1048576,
            request_timeout_seconds=5,
        )


def test_invalid_trusted_hosts_rejects_malformed_host():
    from app.core.config import Settings

    with pytest.raises(ValueError, match=r"Invalid trusted host 'bad_host!'"):
        Settings(
            app_name="API Studio AI Backend",
            environment="development",
            database_url="sqlite:///./test.db",
            secret_key="x" * 32,
            refresh_secret_key="y" * 32,
            cors_origins="http://localhost:3000",
            trusted_hosts="bad_host!",
            max_request_size=1048576,
            max_upload_size=1048576,
            max_response_size=1048576,
            request_timeout_seconds=5,
        )


def test_sensitive_data_is_not_logged(client, caplog):
    caplog.set_level(logging.INFO, logger="app")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logging.getLogger("app").addHandler(handler)

    client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "SuperSecretPassword123!"},
        headers={"Authorization": "Bearer secret.jwt.token"},
    )

    logging.getLogger("app").removeHandler(handler)
    logs = stream.getvalue()

    assert "SuperSecretPassword123!" not in logs
    assert "secret.jwt.token" not in logs
    assert "Authorization" not in logs
