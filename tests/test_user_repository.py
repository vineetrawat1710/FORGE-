from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.user import User
from app.repositories.user_repository import UserRepository


def _make_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return SessionLocal()


def test_repository_create_and_get_by_id_email_and_username():
    db = _make_session()
    repo = UserRepository(db)

    user = User(
        email="alice@example.com",
        username="alice_01",
        password_hash="hashed-password",
    )

    created = repo.create(user)
    assert created.id is not None

    by_id = repo.get_by_id(created.id)
    assert by_id is not None
    assert by_id.email == "alice@example.com"

    by_email = repo.get_by_email("alice@example.com")
    assert by_email is not None
    assert by_email.username == "alice_01"

    by_username = repo.get_by_username("alice_01")
    assert by_username is not None
    assert by_username.email == "alice@example.com"

    db.close()


def test_repository_update_and_delete_user():
    db = _make_session()
    repo = UserRepository(db)

    user = User(
        email="bob@example.com",
        username="bob_01",
        password_hash="hashed-password",
    )

    created = repo.create(user)
    updated = repo.update(created.id, {"email": "bob.new@example.com", "username": "bob_02"})

    assert updated is not None
    assert updated.email == "bob.new@example.com"
    assert updated.username == "bob_02"

    deleted = repo.delete(created.id)
    assert deleted is True
    assert repo.get_by_id(created.id) is None

    db.close()
