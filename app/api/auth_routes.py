"""Auth API router for Job_Booster application."""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.middleware.auth_middleware import get_current_user_dependency
from app.models.api_models import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserProfileResponse,
)
from app.models.db_models import User
from app.services.auth_service import AuthService

router = APIRouter(tags=["Auth"])


@router.post("/auth/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    result = AuthService.register_user(request.email, request.password, request.name)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
    return AuthResponse(**result)


@router.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    user = AuthService.authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = AuthService.create_access_token({"sub": str(user.id), "email": user.email})
    return AuthResponse(
        success=True,
        message="Login successful",
        token=token,
        user={"id": user.id, "email": user.email, "name": user.name},
    )


@router.get("/auth/me", response_model=UserProfileResponse)
async def get_me(current_user: User = Depends(get_current_user_dependency)):
    return UserProfileResponse(
        success=True,
        user={
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "profile_json": current_user.profile_json,
            "created_at": str(current_user.created_at) if current_user.created_at else None,
        },
    )


@router.put("/auth/profile", response_model=UserProfileResponse)
async def update_profile(
    updates: dict,
    current_user: User = Depends(get_current_user_dependency),
):
    from app.services.db_service import get_db_session

    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if "name" in updates:
            user.name = updates["name"]
        if "email" in updates:
            existing = (
                db.query(User).filter(User.email == updates["email"], User.id != user.id).first()
            )
            if existing:
                raise HTTPException(status_code=400, detail="Email already in use")
            user.email = updates["email"]

        profile = user.profile_json or {}
        for key in updates:
            if key not in ("name", "email", "password", "hashed_password"):
                profile[key] = updates[key]
        if "password" in updates:
            profile["hashed_password"] = AuthService.hash_password(updates["password"])
        user.profile_json = profile

        db.commit()
        db.refresh(user)
        return UserProfileResponse(
            success=True,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "profile_json": user.profile_json,
                "created_at": str(user.created_at) if user.created_at else None,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Profile update error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.post("/auth/refresh", response_model=AuthResponse)
async def refresh_token(current_user: User = Depends(get_current_user_dependency)):
    token = AuthService.create_access_token(
        {"sub": str(current_user.id), "email": current_user.email}
    )
    return AuthResponse(
        success=True,
        message="Token refreshed",
        token=token,
        user={"id": current_user.id, "email": current_user.email, "name": current_user.name},
    )
