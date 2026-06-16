"""Optional remote BigSet dataset planning via TinyFish Agent API."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from app.core.config import settings
from app.models.startup_model import UserProfile


@dataclass
class RemoteDatasetResult:
    """Outcome of optional remote dataset automation."""

    goal: str = ""
    attempted: bool = False
    success: bool = False
    message: str = ""
    errors: list[str] = field(default_factory=list)


def profile_to_dataset_goal(profile: UserProfile) -> str:
    """Build a plain-English BigSet dataset goal from user preferences."""
    skills = ", ".join(profile.skills) or "skills inferred from resume"
    roles = ", ".join(profile.target_role_keywords) or "relevant roles"
    locations = ", ".join(profile.preferred_locations) or "any location"
    categories = ", ".join(profile.preferred_categories) or "any industry"
    visa = (
        "must mention visa sponsorship or be open to international candidates"
        if profile.visa_support_required
        else "visa sponsorship not required"
    )
    return (
        "Build a structured hiring dataset of companies currently hiring for roles "
        f"matching: skills [{skills}], target roles [{roles}], "
        f"locations [{locations}], industries/categories [{categories}]. "
        f"Constraints: {visa}. "
        "Include company name, website, location, stage/funding if available, "
        "role titles or open-role counts, and short product/description. "
        "Deduplicate rows and export as CSV with stable column headers."
    )


def _goal_cache_path() -> Path:
    import_dir = Path(getattr(settings, "BIGSET_IMPORT_DIR", "data/bigset_imports"))
    import_dir.mkdir(parents=True, exist_ok=True)
    return import_dir / ".last_dataset_goal.txt"


def persist_dataset_goal(goal: str) -> Path:
    """Save last generated goal for manual BigSet UI use."""
    path = _goal_cache_path()
    path.write_text(goal.strip(), encoding="utf-8")
    return path


async def maybe_request_dataset_build(
    profile: UserProfile,
    *,
    force: bool = False,
) -> RemoteDatasetResult:
    """Optionally run TinyFish Agent against the user's BigSet app URL."""
    goal = profile_to_dataset_goal(profile)
    persist_dataset_goal(goal)

    if not profile.bigset.enabled and not force:
        return RemoteDatasetResult(
            goal=goal,
            message="BigSet disabled in user profile; goal saved for manual use.",
        )

    if not getattr(settings, "BIGSET_REMOTE_ENABLED", False) and not force:
        return RemoteDatasetResult(
            goal=goal,
            message="Remote automation disabled (BIGSET_REMOTE_ENABLED=false).",
        )

    app_url = getattr(settings, "BIGSET_APP_URL", "") or ""
    api_key = os.getenv("TINYFISH_API_KEY") or getattr(settings, "TINYFISH_API_KEY", "")
    if not app_url or not api_key:
        return RemoteDatasetResult(
            goal=goal,
            message="Set BIGSET_APP_URL and TINYFISH_API_KEY to enable remote build.",
        )

    result = RemoteDatasetResult(goal=goal, attempted=True)
    try:
        from tinyfish import AsyncTinyFish

        client = AsyncTinyFish(api_key=api_key)
        automation_goal = (
            f"Open {app_url.rstrip('/')}. If login is required, stop and report that. "
            f"Otherwise start creating a new dataset with this description: {goal}. "
            "Stop after the dataset creation wizard is started or the create form is visible. "
            "Return JSON with keys: status, page_title, notes."
        )
        chunks: list[str] = []
        async with client.agent.stream(url=app_url, goal=automation_goal) as stream:
            async for event in stream:
                chunks.append(str(event))
        result.success = True
        result.message = "\n".join(chunks)[-2000:]
        logger.info("BigSet remote dataset request completed")
    except ImportError:
        result.errors.append("tinyfish package not installed")
        result.message = "Install tinyfish SDK for remote automation."
    except Exception as e:
        result.errors.append(str(e))
        result.message = f"Remote dataset automation failed (non-fatal): {e}"
        logger.warning("BigSet remote automation failed: {}", e)

    return result
