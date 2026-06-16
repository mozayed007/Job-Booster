"""User job-search profile settings (YAML-backed)."""

from fastapi import APIRouter, Depends, HTTPException

from app.middleware.auth_middleware import get_current_user_dependency
from app.models.db_models import User
from app.models.startup_model import UserProfile
from app.services.user_profile_service import load_user_profile, save_user_profile

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/profile")
async def get_profile(_user: User = Depends(get_current_user_dependency)):
    """Return YAML-backed user profile for agents and discovery."""
    profile = load_user_profile()
    return {"success": True, "profile": profile.model_dump()}


@router.put("/profile")
async def put_profile(
    profile: UserProfile,
    _user: User = Depends(get_current_user_dependency),
):
    """Update user profile YAML."""
    try:
        path = save_user_profile(profile)
        return {"success": True, "path": str(path), "profile": profile.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
