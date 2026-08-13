import importlib
import json
from uuid import uuid4

import pytest
import httpx
from fastapi.testclient import TestClient

@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_global_history.db")
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
    import app.routers.history_router as history_router_module
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
    main_module = importlib.reload(main_module)
    
    database_module.Base.metadata.create_all(bind=database_module.engine)

    # Use MockTransport to avoid real HTTP requests while testing the full pipeline
    import httpx
    
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/json"}, text='{"ok":true}', request=request)
        
    async def mock_get_client(self):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))
        
    monkeypatch.setattr(execution_service_module.ExecutionService, "_get_client", mock_get_client)

    database_module.Base.metadata.create_all(bind=database_module.engine)

    return TestClient(main_module.app)

def auth_headers(client: TestClient, username_suffix: str = None) -> dict[str, str]:
    if not username_suffix:
        username_suffix = uuid4().hex[:8]
    email = f"user_{username_suffix}@example.com"
    username = f"user_{username_suffix}"
    client.post("/api/v1/auth/register", json={"email": email, "username": username, "password": "StrongPass1!"})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPass1!"}).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_global_history_authenticated_access(client):
    res = client.get("/api/v1/history")
    assert res.status_code == 401

    headers = auth_headers(client)
    res = client.get("/api/v1/history", headers=headers)
    assert res.status_code == 200
    assert "items" in res.json()["data"]


def test_global_history_empty_and_multiple_requests(client):
    headers = auth_headers(client)
    
    # 1. Empty history
    res = client.get("/api/v1/history", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["data"]["items"]) == 0

    # Create multiple requests
    req1 = client.post("/api/v1/requests", json={"name": "Req1", "method": "GET", "url": "http://example.com/1"}, headers=headers).json()["data"]
    req2 = client.post("/api/v1/requests", json={"name": "Req2", "method": "POST", "url": "http://example.com/2"}, headers=headers).json()["data"]

    # Execute them
    # First execution will fail because it's a real request, but the history is still recorded
    client.post(f"/api/v1/requests/{req1['id']}/execute", headers=headers)
    client.post(f"/api/v1/requests/{req2['id']}/execute", headers=headers)
    client.post(f"/api/v1/requests/{req1['id']}/execute", headers=headers)

    # 2. Multiple requests in history, ordered newest first
    res = client.get("/api/v1/history", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    items = data["items"]
    # Newest should be req1 (the 3rd execution)
    assert items[0]["request_id"] == req1["id"]
    assert items[0]["method"] == "GET"
    assert items[0]["url"] == "http://example.com/1"
    
    # Middle is req2
    assert items[1]["request_id"] == req2["id"]
    assert items[1]["method"] == "POST"
    
    # Oldest is req1
    assert items[2]["request_id"] == req1["id"]


def test_global_history_ownership_isolation(client):
    user1_headers = auth_headers(client, "1")
    user2_headers = auth_headers(client, "2")
    
    req1 = client.post("/api/v1/requests", json={"name": "Req1", "method": "GET", "url": "http://example.com/1"}, headers=user1_headers).json()["data"]
    client.post(f"/api/v1/requests/{req1['id']}/execute", headers=user1_headers)
    
    # User 1 has 1 item
    res1 = client.get("/api/v1/history", headers=user1_headers)
    assert res1.json()["data"]["total"] == 1
    
    # User 2 has 0 items
    res2 = client.get("/api/v1/history", headers=user2_headers)
    assert res2.json()["data"]["total"] == 0


def test_global_history_pagination(client):
    headers = auth_headers(client)
    req = client.post("/api/v1/requests", json={"name": "Req1", "method": "GET", "url": "http://example.com/1"}, headers=headers).json()["data"]
    
    # Execute 3 times
    for _ in range(3):
        client.post(f"/api/v1/requests/{req['id']}/execute", headers=headers)
        
    res = client.get("/api/v1/history?page=1&limit=2", headers=headers)
    assert res.json()["data"]["total"] == 3
    assert len(res.json()["data"]["items"]) == 2
    
    res2 = client.get("/api/v1/history?page=2&limit=2", headers=headers)
    assert res2.json()["data"]["total"] == 3
    assert len(res2.json()["data"]["items"]) == 1


def test_global_history_deleted_request(client):
    headers = auth_headers(client)
    req = client.post("/api/v1/requests", json={"name": "ReqToDelete", "method": "PUT", "url": "http://example.com/delete_me"}, headers=headers).json()["data"]
    
    # Execute it
    client.post(f"/api/v1/requests/{req['id']}/execute", headers=headers)
    
    # Verify in history
    res = client.get("/api/v1/history", headers=headers)
    assert res.json()["data"]["total"] == 1
    assert res.json()["data"]["items"][0]["request_id"] == req["id"]
    
    # Delete request
    client.delete(f"/api/v1/requests/{req['id']}", headers=headers)
    
    # Check history again, should still be there, but request_id should be null
    res = client.get("/api/v1/history", headers=headers)
    assert res.json()["data"]["total"] == 1
    item = res.json()["data"]["items"][0]
    assert item["request_id"] is None
    assert item["method"] == "PUT"
    assert item["url"] == "http://example.com/delete_me"

def test_history_replay_security(client):
    user_a_headers = auth_headers(client, "alice")
    user_b_headers = auth_headers(client, "bob")

    # User A creates environment
    env_res = client.post("/api/v1/environments", headers=user_a_headers, json={
        "name": "Production",
        "variables": {"api_token": {"value": "supersecret123", "secret": True}}
    })
    assert env_res.status_code == 201
    env_id = env_res.json()["data"]["id"]

    # User A creates request
    req_res = client.post("/api/v1/requests", headers=user_a_headers, json={
        "name": "Test Auth",
        "method": "GET",
        "url": "http://example.com/api",
        "environment_id": env_id,
        "authorization": {"type": "bearer", "token": "{{api_token}}"},
        "headers": [],
        "query_parameters": []
    })
    assert req_res.status_code == 201
    req_id = req_res.json()["data"]["id"]

    # User A executes request to create history
    exec_res = client.post(f"/api/v1/requests/{req_id}/execute", headers=user_a_headers)
    assert exec_res.status_code == 200

    # Get history
    hist_res = client.get(f"/api/v1/requests/{req_id}/history", headers=user_a_headers)
    history_id = hist_res.json()["data"]["items"][0]["id"]

    # 1. Unauthenticated users cannot replay history
    unauth_res = client.post(f"/api/v1/history/{history_id}/replay")
    assert unauth_res.status_code == 401

    # 2. User B cannot replay User A's history
    b_replay = client.post(f"/api/v1/history/{history_id}/replay", headers=user_b_headers)
    assert b_replay.status_code == 404 # Do not reveal existence

    # 3. Original history remains unchanged when User A replays
    client.get(f"/api/v1/history/{history_id}", headers=user_a_headers)
    
    replay_res = client.post(f"/api/v1/history/{history_id}/replay", headers=user_a_headers)
    assert replay_res.status_code == 200

    # 4. Replay creates NEW history record
    hist_res2 = client.get(f"/api/v1/requests/{req_id}/history", headers=user_a_headers)
    assert hist_res2.json()["data"]["total"] == 2
    
    # 5. Deleted request check
    client.delete(f"/api/v1/requests/{req_id}", headers=user_a_headers)
    replay_del = client.post(f"/api/v1/history/{history_id}/replay", headers=user_a_headers)
    assert replay_del.status_code == 200
    
    # 6. Environment deletion safety
    client.delete(f"/api/v1/environments/{env_id}", headers=user_a_headers)
    replay_no_env = client.post(f"/api/v1/history/{history_id}/replay", headers=user_a_headers)
    assert replay_no_env.status_code == 404
