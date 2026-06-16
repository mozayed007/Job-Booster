"""Shared security helpers for profile runtimes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROFILES_DIR = Path(__file__).parent.parent
AGENTS_DIR = PROFILES_DIR / "agents"


class ProfileNotAllowedError(ValueError):
    """Raised when a requested profile name is outside the allowed set."""


def _allowed_profile_names() -> frozenset[str]:
    """Return the set of profile names declared in profiles/agents/*.yaml."""
    names: set[str] = set()
    if not AGENTS_DIR.exists():
        return frozenset(names)
    for path in AGENTS_DIR.glob("*.yaml"):
        try:
            with open(path, encoding="utf-8") as f:
                profile = yaml.safe_load(f)
            key = profile.get("meta", {}).get("name")
            if isinstance(key, str) and key:
                names.add(key)
        except Exception:
            # Ignore unreadable profile files during enumeration.
            continue
    return frozenset(names)


_ALLOWED_PROFILE_NAMES: frozenset[str] | None = None


def get_allowed_profile_names() -> frozenset[str]:
    """Lazy-loaded allowlist of agent profile names."""
    global _ALLOWED_PROFILE_NAMES
    if _ALLOWED_PROFILE_NAMES is None:
        _ALLOWED_PROFILE_NAMES = _allowed_profile_names()
    return _ALLOWED_PROFILE_NAMES


def validate_profile_name(profile_name: Any) -> str:
    """Validate that ``profile_name`` is a non-empty, allow-listed profile.

    Blocks path traversal (``../``) and any name not declared in
    ``profiles/agents/*.yaml``. This prevents callers from using a
    profile-name parameter to read arbitrary YAML files outside the
    agents directory.
    """
    if not isinstance(profile_name, str) or not profile_name:
        raise ProfileNotAllowedError("Profile name must be a non-empty string")

    # Reject path separators and parent-directory references outright.
    if "/" in profile_name or "\\" in profile_name or profile_name in {".", ".."}:
        raise ProfileNotAllowedError(f"Invalid profile name: {profile_name!r}")

    allowed = get_allowed_profile_names()
    if allowed and profile_name not in allowed:
        raise ProfileNotAllowedError(
            f"Profile not allowed: {profile_name!r}. Allowed profiles: {sorted(allowed)}"
        )
    return profile_name
