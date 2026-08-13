import importlib
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
async def test_production_blocks_localhost(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_LOCALHOST_TARGETS", "0")

    import app.core.config as config_module
    import app.services.execution_service as exec_module
    importlib.reload(config_module)
    importlib.reload(exec_module)

    db_session = _create_db_session()
    from app.services.user_service import UserService
    from app.services.request_service import RequestService
    from app.services.environment_service import EnvironmentService
    from app.schemas.user import UserCreate
    from app.schemas.environment import EnvironmentCreate
    from app.schemas.request import RequestCreate, RequestHeaderBase, RequestQueryParameterBase, RequestAuthorizationBase

    user_service = UserService(db_session)
    user = user_service.register(UserCreate(email="prod@test.com", username="prod", password="StrongPass1!"))
    env_service = EnvironmentService(db_session)
    environment = env_service.create(user, EnvironmentCreate(name="prod", variables={}, is_active=False))

    request_service = RequestService(db_session)
    created = request_service.create(
        user,
        RequestCreate(
            name="Local Echo",
            method="GET",
            url="http://127.0.0.1:8001/echo",
            body=None,
            body_type="none",
            timeout=5,
            follow_redirects=True,
            verify_ssl=False,
            environment_id=environment.id,
            headers=[],
            query_parameters=[],
            authorization=RequestAuthorizationBase(type="none"),
        ),
    )

    service = exec_module.ExecutionService(db_session)
    with pytest.raises(exec_module.InvalidRequestURLError):
        await service.execute(user, created.id)
