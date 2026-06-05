"""Shared pytest fixtures — in-memory SQLite and scanner reset."""

import pytest
import sqlalchemy.orm as orm
from sqlalchemy.pool import StaticPool

from app.models.db_models import Base, create_tables
from sqlalchemy import create_engine


@pytest.fixture(autouse=True)
def memory_db(monkeypatch):
    """Use isolated in-memory DB for API and service tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_tables(engine)
    session_factory = orm.sessionmaker(bind=engine)

    def _session():
        return session_factory()

    monkeypatch.setattr("app.services.db_service.get_db_session", _session)
    monkeypatch.setattr("app.services.auth_service.get_db_session", _session)

    import app.api.scanner_routes as scanner_routes

    scanner_routes._agent = None

    yield

    Base.metadata.drop_all(engine)
    scanner_routes._agent = None


@pytest.fixture
def auth_token(memory_db):
    """Register a user and return Bearer token for protected routes."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.auth_service import AuthService

    AuthService.register_user("pytest@jobbooster.test", "testpass123", "Pytest")
    client = TestClient(app)
    resp = client.post(
        "/api/auth/login",
        json={"email": "pytest@jobbooster.test", "password": "testpass123"},
    )
    data = resp.json()
    assert data.get("success"), data
    return data["token"]