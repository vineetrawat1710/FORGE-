from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.exceptions import UserAlreadyExistsError, UsernameAlreadyExistsError
from app.schemas.user import UserCreate
from app.services.user_service import UserService


def _make_service():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return UserService(SessionLocal())


def test_register_user_success():
    service = _make_service()

    created = service.register(
        UserCreate(
            email="alice@example.com",
            username="alice_01",
            password="StrongPass1!",
        )
    )

    assert created.email == "alice@example.com"
    assert created.username == "alice_01"
    assert created.is_active is True
    assert "password" not in created.model_dump()


def test_register_user_duplicate_email_raises_service_error():
    service = _make_service()

    service.register(
        UserCreate(
            email="alice@example.com",
            username="alice_01",
            password="StrongPass1!",
        )
    )

    try:
        service.register(
            UserCreate(
                email="alice@example.com",
                username="alice_02",
                password="AnotherPass2@",
            )
        )
    except UserAlreadyExistsError:
        return

    raise AssertionError("Expected UserAlreadyExistsError")


def test_register_user_duplicate_username_raises_service_error():
    service = _make_service()

    service.register(
        UserCreate(
            email="alice@example.com",
            username="alice_01",
            password="StrongPass1!",
        )
    )

    try:
        service.register(
            UserCreate(
                email="bob@example.com",
                username="alice_01",
                password="AnotherPass2@",
            )
        )
    except UsernameAlreadyExistsError:
        return

    raise AssertionError("Expected UsernameAlreadyExistsError")
