from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.schemas.user import LoginRequest, RegisterRequest
from app.services.user_service import UserService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


def test_register_and_login_user(db_session):
    service = UserService(db_session)

    created = service.register(
        RegisterRequest(email="user@example.com", username="alpha", password="Secret123")
    )

    assert created.email == "user@example.com"
    assert created.username == "alpha"
    assert created.is_active is True

    token = service.login(LoginRequest(email="user@example.com", password="Secret123"))

    assert token.token_type == "bearer"
    assert token.access_token


def test_duplicate_email_is_rejected(db_session):
    service = UserService(db_session)

    service.register(RegisterRequest(email="user@example.com", username="alpha", password="Secret123"))

    with pytest.raises(HTTPException) as exc_info:
        service.register(RegisterRequest(email="user@example.com", username="beta", password="Secret456"))

    assert exc_info.value.status_code == 409


def test_duplicate_username_is_rejected(db_session):
    service = UserService(db_session)

    service.register(RegisterRequest(email="user@example.com", username="alpha", password="Secret123"))

    with pytest.raises(HTTPException) as exc_info:
        service.register(RegisterRequest(email="other@example.com", username="alpha", password="Secret456"))

    assert exc_info.value.status_code == 409
