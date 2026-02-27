"""Main FastAPI application for Job_Booster."""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.agents.resume_tailor import ResumeTailoringAgent
from app.core.config import settings
from app.models.api_models import (
    AnalysisRequest,
    AnalysisResponse,
    JobParseRequest,
    JobParseResponse,
    ResumeParseResponse,
    TailoredResumeRequest,
    TailoredResumeResponse,
    AnalysisData,
    SkillMatch,
    TailoredResumeData,
)
from app.services.db_service import (
    AnalysisResultCreateData,
    DatabaseService,
    JobPostingCreateData,
    ResumeCreateData,
    TailoredResumeCreateData,
    get_db_session,
    initialize_database_tables,
)
from app.services.llm_service import LLMService
from app.services.parsing_service import JobParser, ResumeParser

# ---------------------------------------------------------------------------
# Logging initialisation
# ---------------------------------------------------------------------------

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger.info("Initializing Job_Booster API")

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Job_Booster API",
    description="API for tailoring resumes to job descriptions using LLM-powered agents",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Shared service singletons (created once at startup)
# ---------------------------------------------------------------------------

_llm_service: LLMService | None = None
_resume_parser: ResumeParser | None = None
_job_parser: JobParser | None = None
_tailor_agent: ResumeTailoringAgent | None = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def get_resume_parser() -> ResumeParser:
    global _resume_parser
    if _resume_parser is None:
        _resume_parser = ResumeParser(llm_service=get_llm_service())
    return _resume_parser


def get_job_parser() -> JobParser:
    global _job_parser
    if _job_parser is None:
        _job_parser = JobParser(llm_service=get_llm_service())
    return _job_parser


def get_tailor_agent() -> ResumeTailoringAgent:
    global _tailor_agent
    if _tailor_agent is None:
        _tailor_agent = ResumeTailoringAgent(
            llm_service=get_llm_service(),
            resume_parser=get_resume_parser(),
            job_parser=get_job_parser(),
        )
    return _tailor_agent


# ---------------------------------------------------------------------------
# Startup / shutdown events
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event() -> None:
    """Initialise the database tables and warm up services."""
    logger.info("Application startup: initialising database…")
    initialize_database_tables()
    # Pre-warm services so the first request is not slow
    get_tailor_agent()
    logger.info("Application startup complete.")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "message": "Job_Booster API is running",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
    }


@app.get("/health", tags=["Health"])
async def detailed_health() -> Dict[str, Any]:
    """Detailed health check including dependency status."""
    db_ok = False
    try:
        session = get_db_session()
        session.execute(__import__("sqlalchemy").text("SELECT 1"))
        session.close()
        db_ok = True
    except Exception as exc:
        logger.warning(f"DB health check failed: {exc}")

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unavailable",
        "llm": "configured" if settings.GOOGLE_GEMINI_API_KEY else "not configured (mock mode)",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Resume parsing endpoint
# ---------------------------------------------------------------------------


@app.post("/api/parse/resume", response_model=ResumeParseResponse, tags=["Parsing"])
async def parse_resume_endpoint(
    file: UploadFile = File(...),
    resume_parser: ResumeParser = Depends(get_resume_parser),
) -> ResumeParseResponse:
    """Upload and parse a resume file (PDF, DOCX, or TXT).

    Returns structured resume data extracted by the LLM.
    """
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "image/png",
        "image/jpeg",
    }
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}",
        )

    try:
        content = await file.read()
        filename = file.filename or "resume"
        resume = await resume_parser.parse_resume_file_content(content, filename)

        # Persist to database
        db = get_db_session()
        try:
            db_service = DatabaseService(db)
            resume_id = db_service.store_resume(
                ResumeCreateData(
                    title=filename,
                    content=resume.raw_text,
                    parsed_data=resume.model_dump(),
                    file_type=filename.rsplit(".", 1)[-1] if "." in filename else None,
                )
            )
        finally:
            db.close()

        return ResumeParseResponse(
            success=True,
            message="Resume parsed successfully.",
            resume=resume,
            raw_text=resume.raw_text,
        )
    except Exception as exc:
        logger.error(f"parse_resume_endpoint error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Job description parsing endpoint
# ---------------------------------------------------------------------------


@app.post("/api/parse/job", response_model=JobParseResponse, tags=["Parsing"])
async def parse_job_endpoint(
    request: JobParseRequest,
    job_parser: JobParser = Depends(get_job_parser),
) -> JobParseResponse:
    """Parse a raw job description text.

    Returns structured job posting data extracted by the LLM.
    """
    try:
        job = job_parser.parse_job_text(request.job_text)

        # Persist to database
        db = get_db_session()
        try:
            db_service = DatabaseService(db)
            db_service.store_job_posting(
                JobPostingCreateData(
                    title=job.title,
                    company=job.company.name if job.company else None,
                    description=request.job_text,
                    parsed_data=job.model_dump(),
                )
            )
        finally:
            db.close()

        return JobParseResponse(
            success=True,
            message="Job description parsed successfully.",
            job=job,
            raw_text=request.job_text,
        )
    except Exception as exc:
        logger.error(f"parse_job_endpoint error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Analysis endpoint
# ---------------------------------------------------------------------------


@app.post("/api/analyze", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze_endpoint(
    request: AnalysisRequest,
    tailor_agent: ResumeTailoringAgent = Depends(get_tailor_agent),
) -> AnalysisResponse:
    """Analyse the match between a resume and a job description.

    Accepts either stored IDs or raw data dicts.
    """
    resume_data: Dict[str, Any] = {}
    job_data: Dict[str, Any] = {}

    db = get_db_session()
    try:
        db_service = DatabaseService(db)

        if request.resume_id:
            record = db_service.get_record_by_id("resumes", request.resume_id)
            if record and record.get("parsed_data"):
                resume_data = record["parsed_data"]
            else:
                raise HTTPException(status_code=404, detail=f"Resume '{request.resume_id}' not found.")
        elif request.resume_data:
            resume_data = request.resume_data

        if request.job_id:
            record = db_service.get_record_by_id("job_postings", request.job_id)
            if record and record.get("parsed_data"):
                job_data = record["parsed_data"]
            else:
                raise HTTPException(status_code=404, detail=f"Job posting '{request.job_id}' not found.")
        elif request.job_data:
            job_data = request.job_data

    finally:
        db.close()

    if not resume_data and not job_data:
        # Return empty analysis rather than error
        return AnalysisResponse(
            success=True,
            message="No resume or job data provided.",
            analysis=AnalysisData(),
        )

    try:
        from app.models.resume_model import Resume
        from app.models.job_model import JobPosting

        resume = Resume(**resume_data) if resume_data else Resume()
        job = JobPosting(**job_data) if job_data else JobPosting()

        result = tailor_agent.analyze_match(resume, job)

        analysis = AnalysisData(
            match_score=result.get("match_score", 0.0),
            matched_skills=[
                SkillMatch(skill=s, in_resume=True, in_job=True)
                for s in result.get("matched_skills", [])
            ],
            missing_skills=result.get("missing_skills", []),
            strengths=result.get("strengths", []),
            gaps=result.get("gaps", []),
            recommendations=result.get("recommendations", []),
        )

        # Persist analysis result
        db = get_db_session()
        try:
            db_service = DatabaseService(db)
            db_service.store_analysis_result(
                AnalysisResultCreateData(
                    resume_id=request.resume_id,
                    job_posting_id=request.job_id,
                    match_score=analysis.match_score,
                    analysis_data=result,
                )
            )
        finally:
            db.close()

        return AnalysisResponse(
            success=True,
            message="Analysis complete.",
            analysis=analysis,
            resume_id=request.resume_id,
            job_id=request.job_id,
        )
    except Exception as exc:
        logger.error(f"analyze_endpoint error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Tailored resume generation endpoint
# ---------------------------------------------------------------------------


@app.post("/api/tailor", response_model=TailoredResumeResponse, tags=["Tailoring"])
async def tailor_endpoint(
    request: TailoredResumeRequest,
    tailor_agent: ResumeTailoringAgent = Depends(get_tailor_agent),
) -> TailoredResumeResponse:
    """Generate a tailored resume for a specific job description.

    Accepts either stored IDs or raw data dicts.
    """
    resume_data: Dict[str, Any] = {}
    job_data: Dict[str, Any] = {}
    resume_id = request.resume_id
    job_id = request.job_id

    db = get_db_session()
    try:
        db_service = DatabaseService(db)

        if request.resume_id:
            record = db_service.get_record_by_id("resumes", request.resume_id)
            if record and record.get("parsed_data"):
                resume_data = record["parsed_data"]
            else:
                raise HTTPException(status_code=404, detail=f"Resume '{request.resume_id}' not found.")
        elif request.resume_data:
            resume_data = request.resume_data

        if request.job_id:
            record = db_service.get_record_by_id("job_postings", request.job_id)
            if record and record.get("parsed_data"):
                job_data = record["parsed_data"]
            else:
                raise HTTPException(status_code=404, detail=f"Job posting '{request.job_id}' not found.")
        elif request.job_data:
            job_data = request.job_data

    finally:
        db.close()

    try:
        result = tailor_agent.generate_tailored_resume(
            resume_data=resume_data,
            job_data=job_data,
            format_type=request.format_type,
        )

        tailored_data = TailoredResumeData(
            content=result.get("tailored_content", ""),
            format_type=request.format_type,
            improvements=result.get("improvements", []),
            match_score=result.get("match_score"),
        )

        # Persist
        db = get_db_session()
        try:
            db_service = DatabaseService(db)
            tailored_id = db_service.store_tailored_resume(
                TailoredResumeCreateData(
                    original_resume_id=resume_id,
                    job_posting_id=job_id,
                    content=tailored_data.content,
                    format=request.format_type,
                    improvements={"improvements": result.get("improvements", [])},
                )
            )
        finally:
            db.close()

        return TailoredResumeResponse(
            success=True,
            message="Tailored resume generated successfully.",
            tailored_resume=tailored_data,
            resume_id=resume_id,
            job_id=job_id,
            tailored_resume_id=tailored_id,
        )
    except Exception as exc:
        logger.error(f"tailor_endpoint error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Uvicorn entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
