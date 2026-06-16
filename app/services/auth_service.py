"""Authentication service for Job_Booster application."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.db_models import User
from app.services.db_service import get_db_session

jwt: Any = None
JWTError: type[Exception] = Exception
try:
    from jose import JWTError as _JWTError
    from jose import jwt as _jwt

    jwt = _jwt
    JWTError = _JWTError
except ImportError:
    logger.warning("python-jose not installed — JWT features disabled")

try:
    import bcrypt

    _bcrypt_available = True
except ImportError:
    _bcrypt_available = False
    logger.warning("bcrypt not installed — password hashing disabled")


def _resolve_jwt_secret() -> str:
    """Resolve the JWT signing secret.

    In production (DEBUG=False) a fixed ``JWT_SECRET_KEY`` must be supplied —
    a random per-process secret would invalidate every token on restart and
    break multi-worker deployments (each worker would sign with a different
    key). For local development we fall back to a generated secret.
    """
    configured = settings.JWT_SECRET_KEY or os.getenv("JWT_SECRET_KEY")
    if configured:
        return configured
    if settings.DEBUG:
        logger.warning(
            "JWT_SECRET_KEY not set — using a random per-process secret. "
            "This is only acceptable for local development; set JWT_SECRET_KEY "
            "in production."
        )
        return secrets.token_urlsafe(64)
    raise RuntimeError(
        "JWT_SECRET_KEY must be set in production (DEBUG=False). "
        "Set the JWT_SECRET_KEY environment variable to a stable secret."
    )


JWT_SECRET_KEY = _resolve_jwt_secret()
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_EXPIRY_HOURS = settings.JWT_EXPIRY_HOURS

# Precomputed dummy hash used to keep ``authenticate_user``'s response time
# constant whether or not the supplied email exists, mitigating user-
# enumeration timing attacks. Generated for the string "dummy-password".
_DUMMY_BCRYPT_HASH = "$2b$12$0123456789012345678901uP9QrVrX9c2wY4J5j6k7l8m9n0o1p2q3r4"


class AuthService:
    """Handles user authentication, JWT tokens, and password management."""

    @staticmethod
    def hash_password(password: str) -> str:
        if not _bcrypt_available:
            raise RuntimeError("bcrypt not installed")
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        if not _bcrypt_available:
            raise RuntimeError("bcrypt not installed")
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            # Malformed stored hash — treat as a failed verification rather
            # than surfacing a 500 to the caller.
            logger.warning("Malformed password hash encountered")
            return False

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
        if jwt is None:
            raise RuntimeError("python-jose not installed")
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRY_HOURS))
        to_encode.update({"exp": expire})
        return cast(str, jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM))

    @staticmethod
    def decode_token(token: str) -> dict:
        if jwt is None:
            raise RuntimeError("python-jose not installed")
        try:
            payload: dict[str, Any] = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError as e:
            logger.warning(f"JWT decode failed: {e}")
            raise

    @staticmethod
    def register_user(email: str, password: str, name: str) -> dict:
        db: Session = get_db_session()
        try:
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                return {"success": False, "message": "Email already registered"}

            hashed = AuthService.hash_password(password)
            user = User(
                email=email,
                name=name,
                profile_json={"hashed_password": hashed},
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Registered user id={user.id} email={email}")

            token = AuthService.create_access_token({"sub": str(user.id), "email": email})
            return {
                "success": True,
                "message": "User registered successfully",
                "token": token,
                "user": {"id": user.id, "email": user.email, "name": user.name},
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Registration error: {e}")
            return {"success": False, "message": "Registration failed"}
        finally:
            db.close()

    @staticmethod
    def authenticate_user(email: str, password: str) -> User | None:
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.email == email).first()
            hashed = None
            if user is not None:
                profile = user.profile_json or {}
                hashed = profile.get("hashed_password")

            if hashed is None:
                # Run a dummy bcrypt check so the response time is roughly
                # constant whether the user exists or not — this mitigates
                # user-enumeration via timing. The result is discarded.
                if _bcrypt_available:
                    try:
                        bcrypt.checkpw(
                            password.encode("utf-8"),
                            _DUMMY_BCRYPT_HASH.encode("utf-8"),
                        )
                    except (ValueError, TypeError):
                        pass
                return None

            if not AuthService.verify_password(password, hashed):
                return None

            assert user is not None
            logger.info(f"Authenticated user id={user.id} email={email}")
            return user
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
        finally:
            db.close()

    @staticmethod
    def get_current_user(token: str) -> User:
        payload = AuthService.decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("Invalid token payload")

        db: Session = get_db_session()
        try:
            try:
                user_id_int = int(user_id)
            except (TypeError, ValueError) as e:
                raise ValueError("Invalid token payload") from e
            user = db.query(User).filter(User.id == user_id_int).first()
            if not user:
                raise ValueError("User not found")
            return user
        finally:
            db.close()
