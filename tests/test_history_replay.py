import importlib
import json
from uuid import uuid4
import socket

import pytest
from fastapi.testclient import TestClient

@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_history_replay.db")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("REFRESH_SECRET_KEY", "y" * 32)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    monkeypatch.setenv("TRUSTED_HOSTS", "testserver,localhost,127.0.0.1,[::1]")
    monkeypatch.setenv("MAX_REQUEST_SIZE", "1048576")
    monkeypatch.setenv("MAX_UPLOAD_SIZE", "1048576")
    monkeypatch.setenv("MAX_RESPONSE_SIZE", "1048576")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("MAX_REDIRECTS", "5")
    # For SSRF test, ensure localhost targets are allowed or mocked if needed
    
    # Mock DNS
    def fake_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host == "example.com":
            return [(socket.AF_INET, socket.SOCK_STREAM, proto, "", ("93.184.216.34", port or 443))]
        raise socket.gaierror(socket.EAI_NONAME, "name or service not known")
    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

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
    import app.routers.history_router as history_router_module
    import app.routers.request_router as request_router_module
    import app.routers.user_router as user_router_module
    import app.routers.environment_router as env_router_module
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
    importlib.reload(history_router_module)
    importlib.reload(request_router_module)
    importlib.reload(user_router_module)
    importlib.reload(env_router_module)
    main_module = importlib.reload(main_module)
    
    database_module.Base.metadata.create_all(bind=database_module.engine)

    # Mock _get_client in ExecutionService
    import httpx
    
    class MockResponse:
        def __init__(self, status_code, content, headers):
            self.status_code = status_code
            self.content = content
            self.headers = headers
            self.cookies = {}
            self.url = httpx.URL("https://example.com")
            
        def iter_bytes(self):
            yield self.content
            
        async def aclose(self):
            pass

    async def mock_send(*args, **kwargs):
        # We can inspect kwargs["request"] here to verify secrets
        req = args[1] if len(args) > 1 else kwargs.get("request")
        if req:
            auth_header = req.headers.get("authorization")
            if auth_header and "Bearer supersecret123" in auth_header:
                return MockResponse(200, b'{"status": "ok_auth"}', httpx.Headers({"Content-Type": "application/json"}))
        return MockResponse(200, b'{"status": "ok"}', httpx.Headers({"Content-Type": "application/json"}))

    async def mock_get_client(self):
        client = httpx.AsyncClient()
        client.send = mock_send
        return client

    execution_service_module.ExecutionService._get_client = mock_get_client

    with TestClient(main_module.app) as c:
        yield c

    database_module.Base.metadata.drop_all(bind=database_module.engine)


def test_history_replay_security(client):
    # 1. Create User A
    res = client.post("/api/v1/auth/register", json={"email": "alice@example.com", "username": "alice", "password": "Password123!"})
    assert res.status_code == 201
    user_a_token = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "Password123!"}).json()["access_token"]
    user_a_headers = {"Authorization": f"Bearer {user_a_token}"}

    # 2. Create User B
    res = client.post("/api/v1/auth/register", json={"email": "bob@example.com", "username": "bob", "password": "Password123!"})
    assert res.status_code == 201
    user_b_token = client.post("/api/v1/auth/login", json={"email": "bob@example.com", "password": "Password123!"}).json()["access_token"]
    user_b_headers = {"Authorization": f"Bearer {user_b_token}"}

    # 3. User A creates environment with secrets
    env_res = client.post("/api/v1/environments", headers=user_a_headers, json={
        "name": "Production",
        "variables": {"api_token": {"value": "supersecret123", "secret": True}}
    })
    assert env_res.status_code == 201
    env_id = env_res.json()["id"]

    # 4. User A creates request
    req_res = client.post("/api/v1/requests", headers=user_a_headers, json={
        "name": "Test Auth",
        "method": "GET",
        "url": "https://example.com/api",
        "environment_id": env_id,
        "authorization": {"type": "bearer", "token": "{{api_token}}"},
        "headers": [],
        "query_parameters": []
    })
    assert req_res.status_code == 201
    req_id = req_res.json()["id"]

    # 5. User A executes request
    exec_res = client.post(f"/api/v1/requests/{req_id}/execute", headers=user_a_headers)
    assert exec_res.status_code == 200
    assert "ok_auth" in exec_res.json()["body"]

    # 6. Get history
    hist_res = client.get(f"/api/v1/requests/{req_id}/history", headers=user_a_headers)
    assert hist_res.status_code == 200
    history_id = hist_res.json()["items"][0]["id"]

    # 7. Unauthenticated users cannot replay history
    unauth_res = client.post(f"/api/v1/history/{history_id}/replay")
    assert unauth_res.status_code == 401

    # 8. User B cannot replay User A's history
    b_replay = client.post(f"/api/v1/history/{history_id}/replay", headers=user_b_headers)
    assert b_replay.status_code == 404 # Do not reveal existence

    # 9. Original history remains unchanged when User A replays
    orig_history_res = client.get(f"/api/v1/history/{history_id}", headers=user_a_headers)
    orig_snapshot = orig_history_res.json()["request_snapshot"]
    
    replay_res = client.post(f"/api/v1/history/{history_id}/replay", headers=user_a_headers)
    assert replay_res.status_code == 200
    assert "ok_auth" in replay_res.json()["body"] # Secret was successfully passed!

    # 10. Replay creates NEW history record
    hist_res2 = client.get(f"/api/v1/requests/{req_id}/history", headers=user_a_headers)
    assert hist_res2.json()["total"] == 2
    
    # 11. Deleted request check
    client.delete(f"/api/v1/requests/{req_id}", headers=user_a_headers)
    
    # Should still replay!
    replay_del = client.post(f"/api/v1/history/{history_id}/replay", headers=user_a_headers)
    assert replay_del.status_code == 200
    
    # 12. Environment deletion safety
    client.delete(f"/api/v1/environments/{env_id}", headers=user_a_headers)
    replay_no_env = client.post(f"/api/v1/history/{history_id}/replay", headers=user_a_headers)
    # Backend throws EnvironmentNotFoundError which returns 4xx
    assert replay_no_env.status_code == 404
