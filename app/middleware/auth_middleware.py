"""Auth middleware for FastAPI dependency injection."""


from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.db_models import User
from app.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user = AuthService.get_current_user(credentials.credentials)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def optional_user_dependency(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    if credentials is None:
        return None
    try:
        return AuthService.get_current_user(credentials.credentials)
    except Exception:
        return None


async def require_admin(
    user: User = Depends(get_current_user_dependency),
) -> User:
    profile = user.profile_json or {}
    if profile.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
