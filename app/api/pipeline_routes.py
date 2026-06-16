"""Unified Application Package Pipeline — one-click apply and agent pipeline runs."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.middleware.auth_middleware import get_current_user_dependency
from app.models.db_models import User
from app.pipelines.engine import load_pipeline_configs, run_pipeline
from app.pipelines.state import PipelineState
from app.services.apply_service import ApplyService
from app.services.db_service import DatabaseService, get_db_session

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

# Pipelines that may exceed HTTP timeouts when run synchronously
_BACKGROUND_PIPELINE_KEYS = frozenset({
    "full_application",
    "resume_only",
    "job_search_only",
    "cover_letter_only",
    "outreach",
    "interview_prep",
})

_background_jobs: dict[str, dict[str, Any]] = {}


def _prune_background_jobs() -> None:
    """Drop expired entries and cap in-memory job history."""
    now = time.time()
    ttl = settings.PIPELINE_BACKGROUND_JOB_TTL_SECONDS
    max_entries = settings.PIPELINE_BACKGROUND_JOB_MAX_ENTRIES

    expired = [
        job_id
        for job_id, job in _background_jobs.items()
        if now - float(job.get("_updated_at", job.get("_created_at", now))) > ttl
    ]
    for job_id in expired:
        del _background_jobs[job_id]

    if len(_background_jobs) <= max_entries:
        return
    ordered = sorted(
        _background_jobs.items(),
        key=lambda item: float(item[1].get("_updated_at", item[1].get("_created_at", 0))),
    )
    for job_id, _ in ordered[: len(_background_jobs) - max_entries]:
        del _background_jobs[job_id]


def _set_background_job(job_id: str, payload: dict[str, Any]) -> None:
    """Store or update a background job record with timestamps."""
    _prune_background_jobs()
    now = time.time()
    existing = _background_jobs.get(job_id, {})
    payload["_created_at"] = existing.get("_created_at", now)
    payload["_updated_at"] = now
    _background_jobs[job_id] = payload


class PipelineRunRequest(BaseModel):
    """Run a named agent pipeline."""

    pipeline_key: str
    resume_text: str = ""
    job_text: str = ""
    cv_text: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)


class PipelineApplyRequest(BaseModel):
    """Request for the unified apply pipeline."""

    resume_id: int | None = None
    job_id: int | None = None
    job_text: str | None = None
    company_name: str | None = None
    hiring_manager: str | None = None
    format_type: str = "text"
    user_id: int | None = None


class PipelineResult(BaseModel):
    """Result of the unified apply pipeline."""

    tailored_content: str = ""
    improvements: list[str] = []
    cover_letter: str = ""
    key_highlights: list[str] = []
    overall_score: float = 0.0
    skill_matches: list[dict] = []
    strengths: list[str] = []
    gaps: list[str] = []
    suggestions: list[str] = []
    application_id: int | None = None
    resume_id: int | None = None
    job_id: int | None = None


def _serialize_artifact(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    return value


def serialize_pipeline_state(state: PipelineState) -> dict[str, Any]:
    """Convert PipelineState to a JSON-serializable dict."""
    artifacts = {
        key: _serialize_artifact(val) for key, val in state.artifacts.items()
    }
    return {
        "pipeline_name": state.pipeline_name,
        "artifacts": artifacts,
        "errors": state.errors,
        "current_step": state.current_step,
        "steps_completed": state.current_step + 1 if not state.errors else state.current_step,
    }


async def _execute_pipeline(request: PipelineRunRequest) -> PipelineState:
    configs = load_pipeline_configs()
    if request.pipeline_key not in configs:
        raise HTTPException(status_code=404, detail=f"Unknown pipeline: {request.pipeline_key}")
    return await run_pipeline(
        pipeline_key=request.pipeline_key,
        resume_text=request.resume_text,
        job_text=request.job_text,
        cv_text=request.cv_text,
        inputs=request.inputs,
    )


@router.get("/list")
async def pipeline_list():
    """List available pipelines from pipelines.yaml."""
    configs = load_pipeline_configs()
    pipelines = [
        {
            "key": key,
            "name": cfg.name,
            "description": cfg.description,
            "schedule": cfg.schedule,
            "steps": [s.agent_key for s in cfg.steps],
        }
        for key, cfg in configs.items()
    ]
    return {"success": True, "pipelines": pipelines}


@router.get("/run/{job_id}")
async def pipeline_run_status(
    job_id: str,
    _user: User = Depends(get_current_user_dependency),
):
    """Poll a background pipeline run."""
    _prune_background_jobs()
    job = _background_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    return {
        "success": True,
        **{k: v for k, v in job.items() if not str(k).startswith("_")},
    }


@router.post("/run")
async def pipeline_run(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks,
    background: bool = Query(False, description="Run in background for long LLM pipelines"),
    _user: User = Depends(get_current_user_dependency),
):
    """Execute a named pipeline and return artifacts and errors."""
    if background:
        if request.pipeline_key not in _BACKGROUND_PIPELINE_KEYS:
            logger.warning(
                "Background run requested for short pipeline '{}'",
                request.pipeline_key,
            )
        job_id = str(uuid.uuid4())
        _set_background_job(
            job_id,
            {"status": "running", "pipeline_key": request.pipeline_key},
        )

        async def _run_bg():
            try:
                state = await _execute_pipeline(request)
                _set_background_job(
                    job_id,
                    {
                        "status": "completed",
                        "pipeline_key": request.pipeline_key,
                        "result": serialize_pipeline_state(state),
                    },
                )
            except HTTPException as e:
                _set_background_job(
                    job_id,
                    {
                        "status": "failed",
                        "pipeline_key": request.pipeline_key,
                        "error": e.detail,
                    },
                )
            except Exception as e:
                logger.error("Background pipeline failed: {}", e)
                _set_background_job(
                    job_id,
                    {
                        "status": "failed",
                        "pipeline_key": request.pipeline_key,
                        "error": str(e),
                    },
                )

        background_tasks.add_task(_run_bg)

        return {
            "success": True,
            "status": "accepted",
            "job_id": job_id,
            "message": "Pipeline running in background. Poll GET /api/pipeline/run/{job_id}.",
        }

    state = await _execute_pipeline(request)
    return {
        "success": True,
        "status": "completed",
        "data": serialize_pipeline_state(state),
    }


@router.post("/apply")
async def pipeline_apply(request: PipelineApplyRequest):
    """Unified application package: tailor + cover letter + analysis + auto-track.

    Accepts either a stored resume_id + job_id pair, or resume_id + job_text (paste).
    Returns the full application package in one response.
    """
    db = get_db_session()
    try:
        svc = ApplyService(DatabaseService(db))

        resume_text, resume_id, resume_record = await svc.resolve_resume_text(
            request.resume_id
        )

        job_text, job_id, company_name = await svc.resolve_job_text(
            request.job_text or "",
            request.job_id,
            request.company_name or "",
        )

        result = await svc.run(
            resume_id=resume_id,
            job_text=job_text,
            company_name=company_name,
            hiring_manager=request.hiring_manager or "",
            format_type=request.format_type,
            user_id=request.user_id,
            resume_record=resume_record,
        )

        return {
            "success": True,
            "message": "Application package generated",
            "data": PipelineResult(**result).model_dump(),
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Pipeline apply error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/apply/file")
async def pipeline_apply_file(
    file: UploadFile = File(...),
    job_text: str = Form(...),
    company_name: str = Form(""),
    hiring_manager: str = Form(""),
    format_type: str = Form("text"),
    user_id: int | None = Form(None),
):
    """Apply with a file upload instead of resume_id.

    Parses the resume, stores it, indexes it, then runs the full pipeline.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    db = get_db_session()
    try:
        svc = ApplyService(DatabaseService(db))
        result = await svc.run_with_file(
            file_content=content,
            filename=file.filename or "resume",
            job_text=job_text,
            company_name=company_name,
            hiring_manager=hiring_manager,
            format_type=format_type,
            user_id=user_id,
        )

        return {
            "success": True,
            "message": "Application package generated",
            "data": PipelineResult(**result).model_dump(),
        }

    except Exception as e:
        logger.error(f"Pipeline apply file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()