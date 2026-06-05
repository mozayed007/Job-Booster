"""Load optional user job-search preferences from YAML (no domain hardcoding)."""

from __future__ import annotations

from pathlib import Path

import yaml
from loguru import logger

from app.core.config import settings
from app.models.startup_model import UserProfile

_DEFAULT_PATH = Path("data/user_profile.yaml")


def load_user_profile(path: Path | None = None) -> UserProfile:
    """Load profile from file if present; otherwise return empty defaults."""
    profile_path = path or Path(getattr(settings, "USER_PROFILE_PATH", str(_DEFAULT_PATH)))
    if not profile_path.exists():
        return UserProfile()
    try:
        raw = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            logger.warning("User profile file is not a mapping: {}", profile_path)
            return UserProfile()
        return UserProfile.model_validate(raw)
    except Exception as e:
        logger.warning("Failed to load user profile from {}: {}", profile_path, e)
        return UserProfile()


def save_user_profile(profile: UserProfile, path: Path | None = None) -> Path:
    """Persist profile to YAML."""
    profile_path = path or Path(getattr(settings, "USER_PROFILE_PATH", str(_DEFAULT_PATH)))
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json")
    profile_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return profile_path


def save_user_profile(profile: UserProfile, path: Path | None = None) -> Path:
    """Persist profile to YAML; creates parent dirs if needed."""
    profile_path = path or Path(getattr(settings, "USER_PROFILE_PATH", str(_DEFAULT_PATH)))
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json")
    profile_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return profile_path