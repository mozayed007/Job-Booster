"""FastAPI Router for Resume & Job parsing, analysis, and tailoring endpoints."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from loguru import logger

from app.agents.cover_letter import generate_cover_letter
from app.agents.resume_tailor import tailor_resume
from app.models.api_models import (
    AnalysisData,
    AnalysisResponse,
    CoverLetterData,
    CoverLetterResponse,
    JobParseResponse,
    JobTextRequest,
    ResumeParseResponse,
    SkillMatch,
    TailoredResumeData,
    TailoredResumeResponse,
)
from app.services.db_service import (
    AnalysisResultCreateData,
    CoverLetterCreateData,
    DatabaseService,
    JobPostingCreateData,
    ResumeCreateData,
    get_db_session,
)
from app.services.export_service import export_content
from app.services.parsing_service import JobParser, ParserLLM, ResumeParser, extract_text
from app.services.search_service import SearchService
from app.services.vector_store import get_vector_store

router = APIRouter(tags=["Resume & Job"])


@router.post("/parse/resume", response_model=ResumeParseResponse)
async def parse_resume(file: UploadFile = File(...)):
    """Upload resume file → extract text → LLM parse → store → return structured data."""
    try:
        content = await file.read()
        if not content:
            return ResumeParseResponse(success=False, message="Empty file uploaded")

        parser = ResumeParser()
        resume = await parser.parse_resume_file_content(content, file.filename)

        # Store in DB
        db = get_db_session()
        try:
            service = DatabaseService(db)
            resume_id = service.store_resume(
                ResumeCreateData(
                    filename=file.filename,
                    parsed_data=resume.model_dump(mode="json"),
                    raw_text=resume.raw_text,
                    version_name=file.filename,
                    file_path=file.filename,
                    file_format=file.filename.rsplit(".", 1)[-1]
                    if "." in file.filename
                    else "unknown",
                )
            )
        finally:
            db.close()

        # Auto-index to vector store
        if resume_id:
            try:
                vs = get_vector_store()
                if vs.is_available:
                    search_svc = SearchService(vector_store=vs)
                    index_text = resume.raw_text or str(resume.model_dump(mode="json"))
                    await search_svc.index_resume(resume_id, index_text)
            except Exception as idx_err:
                logger.warning(f"Auto-index resume failed (non-fatal): {idx_err}")

        return ResumeParseResponse(
            success=True,
            message="Resume parsed successfully",
            data=resume,
            resume_version_id=resume_id,
        )
    except Exception as e:
        logger.error(f"Resume parsing error: {e}")
        return ResumeParseResponse(success=False, message=str(e))


@router.post("/parse/job", response_model=JobParseResponse)
async def parse_job(request: JobTextRequest):
    """Job description text → LLM parse → store → return structured data."""
    try:
        if not request.text.strip():
            return JobParseResponse(success=False, message="Empty job description")

        parser = JobParser()
        job = await parser.parse_job_text(request.text)

        # Store in DB
        db = get_db_session()
        try:
            service = DatabaseService(db)
            job_id = service.store_job_posting(
                JobPostingCreateData(
                    title=job.title,
                    company=job.company_info.name if job.company_info else None,
                    parsed_data=job.model_dump(mode="json"),
                    raw_text=request.text[:5000],
                )
            )
        finally:
            db.close()

        # Auto-index to vector store
        if job_id:
            try:
                vs = get_vector_store()
                if vs.is_available:
                    search_svc = SearchService(vector_store=vs)
                    await search_svc.index_job(job_id, request.text[:5000])
            except Exception as idx_err:
                logger.warning(f"Auto-index job failed (non-fatal): {idx_err}")

        return JobParseResponse(
            success=True,
            message="Job description parsed successfully",
            data=job,
        )
    except Exception as e:
        logger.error(f"Job parsing error: {e}")
        return JobParseResponse(success=False, message=str(e))


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_match(
    file: UploadFile = File(...),
    job_text: str = Form(...),
):
    """Resume file + job text → parse both → run analysis → return match data."""
    try:
        content = await file.read()
        if not content:
            return AnalysisResponse(success=False, message="Empty file")

        resume_parser = ResumeParser()
        resume = await resume_parser.parse_resume_file_content(content, file.filename)

        job_parser = JobParser()
        job = await job_parser.parse_job_text(job_text)

        # Simple analysis
        resume_skills = {s.name.lower() for s in resume.skills}
        required = {s.lower() for s in job.required_skills}
        preferred = {s.lower() for s in job.preferred_skills}
        all_job_skills = required | preferred

        skill_matches = []
        matched = resume_skills & all_job_skills
        for skill in all_job_skills:
            skill_matches.append(
                SkillMatch(
                    skill=skill,
                    matched=skill in matched,
                    confidence=1.0 if skill in matched else 0.0,
                    source="resume" if skill in matched else "job",
                )
            )

        unmatched = all_job_skills - resume_skills
        overall_score = (len(matched) / max(len(all_job_skills), 1)) * 100

        analysis = AnalysisData(
            overall_score=round(overall_score, 1),
            skill_matches=skill_matches,
            strengths=list(matched),
            gaps=list(unmatched),
            suggestions=[f"Add missing skill to resume: {s}" for s in list(unmatched)[:5]],
        )

        db = get_db_session()
        try:
            svc = DatabaseService(db)
            svc.store_analysis_result(
                AnalysisResultCreateData(
                    resume_id=0,
                    job_id=0,
                    analysis_data=analysis.model_dump(),
                )
            )
        finally:
            db.close()

        return AnalysisResponse(
            success=True,
            message="Analysis completed",
            data=analysis,
        )
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return AnalysisResponse(success=False, message=str(e))


@router.post("/tailor", response_model=TailoredResumeResponse)
async def tailor_resume_endpoint(
    file: UploadFile = File(...),
    job_text: str = Form(...),
    format_type: str = Form("text"),
):
    """Resume file + job text + format → run tailor → return tailored resume."""
    try:
        content = await file.read()
        if not content:
            return TailoredResumeResponse(success=False, message="Empty file")

        # Extract resume text
        resume_text = extract_text(content, file.filename)
        if not resume_text.strip():
            return TailoredResumeResponse(success=False, message="Could not extract text from file")

        # Run tailoring
        result = await tailor_resume(resume_text, job_text, format_type)

        return TailoredResumeResponse(
            success=True,
            message="Resume tailored successfully",
            data=TailoredResumeData(
                tailored_content=result.tailored_content,
                improvements=result.improvements,
                format_type=result.format_type,
            ),
        )
    except Exception as e:
        logger.error(f"Tailoring error: {e}")
        return TailoredResumeResponse(success=False, message=str(e))


@router.post("/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter_endpoint(
    file: UploadFile = File(...),
    job_text: str = Form(...),
    company_name: str = Form(None),
    hiring_manager: str = Form(None),
):
    """Resume file + job text → generate cover letter → store → return."""
    try:
        content = await file.read()
        if not content:
            return CoverLetterResponse(success=False, message="Empty file")

        resume_text = extract_text(content, file.filename)
        if not resume_text.strip():
            return CoverLetterResponse(success=False, message="Could not extract text from file")

        result = await generate_cover_letter(resume_text, job_text, company_name, hiring_manager)

        # Store in DB
        db = get_db_session()
        try:
            service = DatabaseService(db)
            service.store_cover_letter(
                CoverLetterCreateData(
                    cover_letter_text=result.cover_letter,
                    key_highlights=result.key_highlights,
                    company_name=company_name,
                )
            )
        finally:
            db.close()

        return CoverLetterResponse(
            success=True,
            message="Cover letter generated",
            data=CoverLetterData(
                cover_letter=result.cover_letter,
                key_highlights=result.key_highlights,
                tone=result.tone,
            ),
        )
    except Exception as e:
        logger.error(f"Cover letter generation error: {e}")
        return CoverLetterResponse(success=False, message=str(e))


@router.post("/tailor-to-template")
async def tailor_to_template(
    file: UploadFile = File(...),
    job_text: str = Form(...),
    format_type: str = Form("latex"),
):
    """Tailor resume → render into template → save + return .tex file."""
    try:
        content = await file.read()
        if not content:
            return Response(content="Empty file", status_code=400)

        # Parse resume into structured model
        resume_text = extract_text(content, file.filename)
        if not resume_text.strip():
            return Response(content="Could not extract text", status_code=400)

        parser = ParserLLM()
        resume = await parser.parse_resume(resume_text)

        # Parse job for title/company
        job = await parser.parse_job(job_text)
        job_title = job.title or "Unknown"
        company = job.company_info.name if job.company_info else ""

        # Tailor the content
        tailor_result = await tailor_resume(resume_text, job_text, "text")

        # Update resume summary with tailored content
        resume.summary = tailor_result.tailored_content[:2000]

        # Render into template
        from app.services.template_engine import get_output_path, render_resume

        tex_content = render_resume(resume)

        # Save to output dir
        output_path = get_output_path(job_title, company, "tex")
        output_path.write_text(tex_content, encoding="utf-8")
        logger.info(f"Saved tailored resume to {output_path}")

        # Return as download
        return Response(
            content=tex_content.encode("utf-8"),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={output_path.name}"},
        )
    except Exception as e:
        logger.error(f"Template tailoring error: {e}")
        return Response(content=f"Error: {e}", status_code=500)


@router.post("/export")
async def export_tailored_resume(
    content: str = Form(...),
    format_type: str = Form("text"),
    title: str = Form("Resume"),
):
    """Export content (resume or cover letter) to the specified format."""
    try:
        result_bytes, media_type = export_content(content, format_type, title)

        ext_map = {
            "text/plain": "txt",
            "text/html": "html",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/pdf": "pdf",
        }
        ext = ext_map.get(media_type, "txt")
        filename = f"{title.lower().replace(' ', '_')}.{ext}"

        return Response(
            content=result_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        logger.error(f"Export error: {e}")
        return Response(content=f"Export failed: {e}", status_code=500)


@router.get("/resume-versions")
async def list_resume_versions():
    """List all stored resume versions."""
    db = get_db_session()
    try:
        service = DatabaseService(db)
        versions = service.query_records("resume_versions", limit=100)
        return {"success": True, "versions": versions}
    finally:
        db.close()


@router.get("/resume-versions/{version_id}")
async def get_resume_version(version_id: int):
    """Get a specific resume version with parsed data."""
    db = get_db_session()
    try:
        service = DatabaseService(db)
        versions = service.query_records(
            "resume_versions",
            filter_conditions={"id": version_id},
        )
        if not versions:
            raise HTTPException(status_code=404, detail="Version not found")
        return {"success": True, "version": versions[0]}
    finally:
        db.close()
