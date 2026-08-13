import importlib
import asyncio
import socket
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _create_db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    import app.core.database as database_module
    import app.models.user as user_model_module
    import app.models.collection as collection_model_module
    import app.models.environment as environment_model_module
    import app.models.request as request_model_module

    importlib.reload(database_module)
    importlib.reload(user_model_module)
    importlib.reload(collection_model_module)
    importlib.reload(environment_model_module)
    importlib.reload(request_model_module)

    database_module.Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()


@pytest.mark.asyncio
async def test_execute_localhost_end_to_end(monkeypatch):
    # Ensure environment enables localhost targets
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOW_LOCALHOST_TARGETS", "1")

    # reload modules that capture settings at import time
    import app.core.config as config_module
    import app.services.execution_service as exec_module
    importlib.reload(config_module)
    importlib.reload(exec_module)

    # Start local test server
    import subprocess
    server = subprocess.Popen([
        "python",
        "-m",
        "uvicorn",
        "_local_test_app:app",
        "--app-dir",
        "tests",
        "--host",
        "127.0.0.1",
        "--port",
        "8001",
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        # wait for server to be available by polling the port
        import time as _time
        import socket as _socket

        deadline = _time.time() + 5.0
        while _time.time() < deadline:
            try:
                s = _socket.socket()
                s.settimeout(0.5)
                s.connect(("127.0.0.1", 8001))
                s.close()
                break
            except Exception:
                _time.sleep(0.1)
        else:
            raise RuntimeError("Local test server did not start in time")

        # create DB session and request
        db_session = _create_db_session()
        from app.services.user_service import UserService
        from app.services.request_service import RequestService
        from app.services.environment_service import EnvironmentService
        from app.schemas.user import UserCreate
        from app.schemas.environment import EnvironmentCreate
        from app.schemas.request import RequestCreate, RequestHeaderBase, RequestQueryParameterBase, RequestAuthorizationBase

        user_service = UserService(db_session)
        user = user_service.register(UserCreate(email="local@test.com", username="local", password="StrongPass1!"))
        env_service = EnvironmentService(db_session)
        environment = env_service.create(user, EnvironmentCreate(name="local", variables={}, is_active=False))

        request_service = RequestService(db_session)
        created = request_service.create(
            user,
            RequestCreate(
                name="Local Echo",
                method="POST",
                url="http://127.0.0.1:8001/echo?x=1",
                body='{"hello":"world"}',
                body_type="json",
                timeout=5,
                follow_redirects=True,
                verify_ssl=False,
                environment_id=environment.id,
                headers=[RequestHeaderBase(key="X-Test", value="t", enabled=True)],
                query_parameters=[RequestQueryParameterBase(key="q", value="1", enabled=True)],
                authorization=RequestAuthorizationBase(type="none"),
            ),
        )

        service = exec_module.ExecutionService(db_session)
        result = await service.execute(user, created.id)

        assert result.status_code == 200
        import json as _json
        payload = _json.loads(result.body)
        # the test server returns the POST body as a string in the `body` field
        assert payload.get("body") == '{"hello":"world"}'

        history, total = service.list_history(user, created.id)
        assert total == 1
    finally:
        server.terminate()
        server.wait()
