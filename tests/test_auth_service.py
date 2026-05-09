"""Tests for auth service."""

from datetime import timedelta

import pytest
import sqlalchemy.orm as orm

from app.models.db_models import Base
from app.services.auth_service import AuthService
from app.services.db_service import get_configured_engine


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    engine = get_configured_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = orm.sessionmaker(bind=engine)
    monkeypatch.setattr("app.services.auth_service.get_db_session", lambda: TestSession())
    yield
    Base.metadata.drop_all(engine)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = AuthService.hash_password("mypassword")
        assert hashed != "mypassword"
        assert AuthService.verify_password("mypassword", hashed) is True

    def test_wrong_password(self):
        hashed = AuthService.hash_password("correct")
        assert AuthService.verify_password("wrong", hashed) is False


class TestJWT:
    def test_create_and_decode(self):
        token = AuthService.create_access_token({"sub": "1", "email": "a@b.com"})
        payload = AuthService.decode_token(token)
        assert payload["sub"] == "1"
        assert payload["email"] == "a@b.com"
        assert "exp" in payload

    def test_custom_expiry(self):
        token = AuthService.create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=5))
        payload = AuthService.decode_token(token)
        assert payload["sub"] == "1"

    def test_invalid_token_raises(self):
        import pytest

        with pytest.raises(Exception):
            AuthService.decode_token("invalid.token.value")

    def test_expired_token_raises(self):
        token = AuthService.create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        import pytest

        with pytest.raises(Exception):
            AuthService.decode_token(token)


class TestRegisterUser:
    def test_register_success(self):
        result = AuthService.register_user("test@example.com", "pass123", "Test User")
        assert result["success"] is True
        assert result["token"] is not None
        assert result["user"]["email"] == "test@example.com"

    def test_duplicate_email(self):
        AuthService.register_user("dup@example.com", "pass123", "User One")
        result = AuthService.register_user("dup@example.com", "pass456", "User Two")
        assert result["success"] is False
        assert "already registered" in result["message"].lower()


class TestAuthenticateUser:
    def test_authenticate_success(self):
        AuthService.register_user("auth@example.com", "secret123", "Auth User")
        user = AuthService.authenticate_user("auth@example.com", "secret123")
        assert user is not None
        assert user.email == "auth@example.com"

    def test_authenticate_wrong_password(self):
        AuthService.register_user("wp@example.com", "secret123", "WP User")
        user = AuthService.authenticate_user("wp@example.com", "wrongpass")
        assert user is None

    def test_authenticate_nonexistent_user(self):
        user = AuthService.authenticate_user("noone@example.com", "pass")
        assert user is None


class TestGetCurrentUser:
    def test_get_current_user_success(self):
        result = AuthService.register_user("me@example.com", "pass123", "Me User")
        token = result["token"]
        user = AuthService.get_current_user(token)
        assert user.email == "me@example.com"

    def test_get_current_user_invalid_token(self):
        import pytest

        with pytest.raises(Exception):
            AuthService.get_current_user("bad.token.here")
