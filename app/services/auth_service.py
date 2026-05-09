"""Authentication service for Job_Booster application."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.models.db_models import User
from app.services.db_service import get_db_session

try:
    from jose import JWTError, jwt
except ImportError:
    jwt = None
    JWTError = Exception
    logger.warning("python-jose not installed — JWT features disabled")

try:
    import bcrypt

    _bcrypt_available = True
except ImportError:
    _bcrypt_available = False
    logger.warning("bcrypt not installed — password hashing disabled")


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(64))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))


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
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        if jwt is None:
            raise RuntimeError("python-jose not installed")
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRY_HOURS))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        if jwt is None:
            raise RuntimeError("python-jose not installed")
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
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
            return {"success": False, "message": str(e)}
        finally:
            db.close()

    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[User]:
        db: Session = get_db_session()
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return None

            profile = user.profile_json or {}
            hashed = profile.get("hashed_password")
            if not hashed:
                return None

            if not AuthService.verify_password(password, hashed):
                return None

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
            user = db.query(User).filter(User.id == int(user_id)).first()
            if not user:
                raise ValueError("User not found")
            return user
        finally:
            db.close()
