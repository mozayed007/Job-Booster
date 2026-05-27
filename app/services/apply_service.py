"""Application orchestration service — one-click apply pipeline.

Encapsulates the full application workflow: resume resolution, job parsing,
skill matching, LLM calls, persistence, indexing, and tracking.
"""

import json
from typing import Any

from loguru import logger

from app.agents.cover_letter import generate_cover_letter
from app.agents.resume_tailor import tailor_resume
from app.models.api_models import AnalysisData, SkillMatch
from app.services.db_service import (
    AnalysisResultCreateData,
    CoverLetterCreateData,
    DatabaseService,
    JobPostingCreateData,
    ResumeCreateData,
    TailoredResumeCreateData,
)
from app.services.parsing_service import JobParser, ResumeParser
from app.services.search_service import SearchService
from app.services.tracking_service import ApplicationTracker
from app.services.vector_store import get_vector_store


def _extract_resume_text(resume_record: dict) -> str:
    """Extract readable text from a resume DB record."""
    text = resume_record.get("raw_text") or ""
    if text:
        return text

    content_json = resume_record.get("content_json")
    if not content_json:
        return ""

    if isinstance(content_json, str):
        try:
            content_json = json.loads(content_json)
        except Exception:
            return ""

    if isinstance(content_json, dict):
        parts = []
        for k in ("summary", "objective", "description"):
            if k in content_json and isinstance(content_json[k], str):
                parts.append(content_json[k])
        return " ".join(parts)
    return ""


def _extract_resume_skills(resume_record: dict) -> set[str]:
    """Extract skill keywords from a resume DB record."""
    skills: set[str] = set()
    content_json = resume_record.get("content_json")
    if not content_json:
        return skills

    if isinstance(content_json, str):
        try:
            content_json = json.loads(content_json)
        except Exception:
            return skills

    if isinstance(content_json, dict):
        for key in ("skills", "technologies", "tools", "required_skills", "preferred_skills"):
            val = content_json.get(key)
            if isinstance(val, list):
                skills.update(
                    s.lower() if isinstance(s, str) else str(s).lower()
                    for s in val
                )
    return skills


def _run_skill_analysis(
    resume_skills: set[str],
    job_skills: set[str],
) -> tuple[list[dict[str, Any]], set[str], set[str], list[str], float]:
    """Compare resume skills against job requirements and return match data."""
    matched = resume_skills & job_skills
    unmatched = job_skills - resume_skills
    overall_score = (len(matched) / max(len(job_skills), 1)) * 100

    skill_matches = [
        {
            "skill": skill,
            "matched": skill in matched,
            "confidence": 1.0 if skill in matched else 0.0,
        }
        for skill in job_skills
    ]
    suggestions = [f"Add missing skill: {s}" for s in sorted(unmatched)[:5]]

    return skill_matches, matched, unmatched, suggestions, overall_score


async def _auto_index_job(job_id: int, text: str) -> None:
    """Index a job posting into the vector store (best-effort)."""
    try:
        vs = get_vector_store()
        if vs.is_available:
            search_svc = SearchService(vector_store=vs)
            await search_svc.index_job(job_id, text[:5000])
    except Exception as e:
        logger.warning(f"Auto-index job failed: {e}")


async def _auto_index_resume(resume_id: int, text: str) -> None:
    """Index a resume into the vector store (best-effort)."""
    try:
        vs = get_vector_store()
        if vs.is_available:
            search_svc = SearchService(vector_store=vs)
            await search_svc.index_resume(resume_id, text)
    except Exception as e:
        logger.warning(f"Auto-index resume failed: {e}")


class ApplyService:
    """Orchestrates the full application pipeline for a resume+job pair."""

    def __init__(self, db_svc: DatabaseService):
        self.db_svc = db_svc

    async def resolve_resume_text(
        self,
        resume_id: int | None,
    ) -> tuple[str, int, dict]:
        """Fetch resume from DB and extract readable text.

        Returns:
            Tuple of (resume_text, resume_id, resume_record).
        """
        if not resume_id:
            return "", 0, {}

        records = self.db_svc.query_records(
            "resumes", limit=1, filter_conditions={"id": resume_id}
        )
        if not records:
            raise ValueError(f"Resume {resume_id} not found")

        record = records[0]
        text = _extract_resume_text(record)
        if not text:
            raise ValueError("Resume has no text content")

        return text, resume_id, record

    async def resolve_job_text(
        self,
        job_text: str,
        job_id: int | None,
        company_name: str,
    ) -> tuple[str, int | None, str]:
        """Resolve job description from text or DB record.

        Returns:
            Tuple of (job_text, job_id, company_name).
        """
        text = job_text or ""
        resolved_id = job_id
        resolved_company = company_name

        if job_id and not text:
            records = self.db_svc.query_records(
                "job_postings", limit=1, filter_conditions={"id": job_id}
            )
            if not records:
                raise ValueError(f"Job {job_id} not found")
            record = records[0]
            text = record.get("raw_text") or ""
            if not resolved_company:
                resolved_company = record.get("company") or ""

        if not text:
            raise ValueError("No job description provided")

        return text, resolved_id, resolved_company

    async def run(
        self,
        resume_id: int,
        job_text: str,
        company_name: str = "",
        hiring_manager: str = "",
        format_type: str = "text",
        user_id: int | None = None,
        resume_record: dict | None = None,
    ) -> dict[str, Any]:
        """Run the full application pipeline.

        Args:
            resume_id: Stored resume ID.
            job_text: Job description text.
            company_name: Optional company name.
            hiring_manager: Optional hiring manager name.
            format_type: Output format (text, html, docx, etc.).
            user_id: Optional user ID for tracking.
            resume_record: Pre-fetched resume record (avoids extra DB query).

        Returns:
            Pipeline result dict matching PipelineResult schema.
        """
        # Resolve resume text
        if resume_record is None:
            records = self.db_svc.query_records(
                "resumes", limit=1, filter_conditions={"id": resume_id}
            )
            resume_record = records[0] if records else None

        if not resume_record:
            raise ValueError(f"Resume {resume_id} not found")

        resume_text = _extract_resume_text(resume_record)
        if not resume_text:
            raise ValueError("Resume has no text content")

        # Run LLM steps
        tailor_result = await tailor_resume(resume_text, job_text, format_type)
        cl_result = await generate_cover_letter(
            resume_text, job_text, company_name, hiring_manager
        )

        # Parse job and run skill analysis
        resume_skills = _extract_resume_skills(resume_record)
        job_parser = JobParser()
        parsed_job = await job_parser.parse_job_text(job_text)

        all_job_skills = {
            s.lower()
            for s in parsed_job.required_skills | parsed_job.preferred_skills
        }
        skill_matches, matched, unmatched, suggestions, overall_score = (
            _run_skill_analysis(resume_skills, all_job_skills)
        )

        # Store job if new
        stored_job_id = None
        if parsed_job.title:
            stored_job_id = self.db_svc.store_job_posting(
                JobPostingCreateData(
                    title=parsed_job.title,
                    company=company_name,
                    parsed_data=parsed_job.model_dump(mode="json"),
                    raw_text=job_text[:5000],
                )
            )
            if stored_job_id:
                await _auto_index_job(stored_job_id, job_text)

        # Persist results
        if resume_id and stored_job_id:
            self.db_svc.store_tailored_resume(
                TailoredResumeCreateData(
                    resume_id=resume_id,
                    job_id=stored_job_id,
                    tailored_content=tailor_result.tailored_content,
                    match_score=round(overall_score, 1),
                )
            )

            analysis = AnalysisData(
                overall_score=round(overall_score, 1),
                skill_matches=[
                    SkillMatch(
                        skill=s["skill"],
                        matched=s["matched"],
                        confidence=s["confidence"],
                        source="resume" if s["matched"] else "job",
                    )
                    for s in skill_matches
                ],
                strengths=list(matched),
                gaps=list(unmatched),
                suggestions=suggestions,
            )
            self.db_svc.store_analysis_result(
                AnalysisResultCreateData(
                    resume_id=resume_id,
                    job_id=stored_job_id,
                    analysis_data=analysis.model_dump(),
                )
            )

            self.db_svc.store_cover_letter(
                CoverLetterCreateData(
                    resume_id=resume_id,
                    job_id=stored_job_id,
                    cover_letter_text=cl_result.cover_letter,
                    key_highlights=cl_result.key_highlights,
                    company_name=company_name,
                )
            )

        # Auto-track application
        application_id = None
        if resume_id and stored_job_id:
            tracker = ApplicationTracker(db_service=self.db_svc)
            application_id = tracker.track_application({
                "user_id": user_id,
                "job_id": stored_job_id,
                "resume_id": resume_id,
                "company_name": company_name or parsed_job.title,
                "position_title": parsed_job.title,
                "status": "applied",
            })

        return {
            "tailored_content": tailor_result.tailored_content,
            "improvements": tailor_result.improvements,
            "cover_letter": cl_result.cover_letter,
            "key_highlights": cl_result.key_highlights,
            "overall_score": round(overall_score, 1),
            "skill_matches": skill_matches,
            "strengths": list(matched),
            "gaps": list(unmatched),
            "suggestions": suggestions,
            "application_id": application_id,
            "resume_id": resume_id,
            "job_id": stored_job_id,
        }

    async def run_with_file(
        self,
        file_content: bytes,
        filename: str,
        job_text: str,
        company_name: str = "",
        hiring_manager: str = "",
        format_type: str = "text",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Parse an uploaded resume file, store it, then run the full pipeline.

        Returns:
            Pipeline result dict matching PipelineResult schema.
        """
        resume_parser = ResumeParser()
        resume = await resume_parser.parse_resume_file_content(file_content, filename)
        resume_text = resume.raw_text or str(resume.model_dump(mode="json"))

        resume_id = self.db_svc.store_resume(
            ResumeCreateData(
                filename=filename,
                parsed_data=resume.model_dump(mode="json"),
                raw_text=resume_text,
                version_name=filename,
                file_path=filename,
                file_format=filename.rsplit(".", 1)[-1] if "." in filename else "unknown",
            )
        )

        if resume_id:
            await _auto_index_resume(resume_id, resume_text)

        return await self.run(
            resume_id=resume_id,
            job_text=job_text,
            company_name=company_name,
            hiring_manager=hiring_manager,
            format_type=format_type,
            user_id=user_id,
        )
