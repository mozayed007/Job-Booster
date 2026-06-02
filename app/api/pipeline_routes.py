"""Unified Application Package Pipeline — one-click apply.

Routes delegate all business logic to ApplyService.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from app.services.apply_service import ApplyService
from app.services.db_service import DatabaseService, get_db_session

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


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


def _get_apply_service() -> ApplyService:
    """Build ApplyService with a fresh DB session."""
    db = get_db_session()
    try:
        return ApplyService(DatabaseService(db))
    except Exception:
        db.close()
        raise


@router.post("/apply")
async def pipeline_apply(request: PipelineApplyRequest):
    """Unified application package: tailor + cover letter + analysis + auto-track.

    Accepts either a stored resume_id + job_id pair, or resume_id + job_text (paste).
    Returns the full application package in one response.
    """
    db = get_db_session()
    try:
        svc = ApplyService(DatabaseService(db))

        # Resolve resume
        resume_text, resume_id, resume_record = await svc.resolve_resume_text(request.resume_id)

        # Resolve job
        job_text, job_id, company_name = await svc.resolve_job_text(
            request.job_text or "",
            request.job_id,
            request.company_name or "",
        )

        # Run pipeline
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
