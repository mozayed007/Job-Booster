"""Discovery sync agent — import BigSet exports before scanner/job-finder pipelines."""

from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import AgentConfig, BaseAgent
from app.core.config import settings
from app.pipelines.state import PipelineState
from app.services.bigset_import_service import import_changed_files_in_dir
from app.services.bigset_remote_service import maybe_request_dataset_build
from app.services.user_profile_service import load_user_profile


class DiscoverySyncOutput(BaseModel):
    """Artifacts from discovery sync."""

    import_files: int = 0
    jobs_stored: int = 0
    startups_upserted: int = 0
    remote_attempted: bool = False
    remote_message: str = ""
    dataset_goal: str = ""
    errors: list[str] = Field(default_factory=list)


class DiscoverySyncAgent(BaseAgent):
    """Sync BigSet folder imports and optional remote dataset planning."""

    output_type = DiscoverySyncOutput

    async def execute(self, state: PipelineState) -> None:
        profile = load_user_profile()
        output = DiscoverySyncOutput()

        force_remote = bool(state.inputs.get("force_remote", False))
        if getattr(settings, "BIGSET_REMOTE_ENABLED", False) or force_remote:
            remote = await maybe_request_dataset_build(profile, force=force_remote)
            output.remote_attempted = remote.attempted
            output.remote_message = remote.message
            output.dataset_goal = remote.goal
            output.errors.extend(remote.errors)

        if profile.bigset.enabled:
            results = await import_changed_files_in_dir()
            output.import_files = len(results)
            for r in results:
                if r.success:
                    output.jobs_stored += r.stored
                    output.startups_upserted += r.startups_upserted
                else:
                    output.errors.extend(r.errors)
            logger.info(
                "Discovery sync: {} files, {} jobs stored",
                output.import_files,
                output.jobs_stored,
            )
        else:
            output.remote_message = (
                output.remote_message or "BigSet import skipped (disabled in profile)."
            )

        state.artifacts["discovery_sync"] = output.model_dump()