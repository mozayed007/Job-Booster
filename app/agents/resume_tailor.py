"""Resume Tailoring Agent implementation using Google ADK.

This agent orchestrates:
1. Resume + job description parsing (via parsing_service)
2. Skill-matching and experience reordering
3. Bullet-point enhancement via LLM
4. Tailored resume generation in the requested output format
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger

from app.models.job_model import JobPosting
from app.models.resume_model import Resume
from app.services.llm_service import LLMService
from app.services.parsing_service import JobParser, ResumeParser


# ---------------------------------------------------------------------------
# ADK tool functions
# These are plain Python functions that the ADK Agent can call as tools.
# They are also invoked directly by the agent logic when ADK is unavailable.
# ---------------------------------------------------------------------------


def highlight_skills(
    resume_skills: List[str],
    job_required_skills: List[str],
    job_preferred_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Identify skill overlap between a resume and a job posting.

    Args:
        resume_skills: Skills listed on the resume.
        job_required_skills: Skills required by the job.
        job_preferred_skills: Nice-to-have skills for the job.

    Returns:
        A dict with matched, missing, and preferred skill lists.
    """
    job_preferred_skills = job_preferred_skills or []

    resume_lower = {s.lower() for s in resume_skills}
    required_lower = {s.lower(): s for s in job_required_skills}
    preferred_lower = {s.lower(): s for s in job_preferred_skills}

    matched = [orig for norm, orig in required_lower.items() if norm in resume_lower]
    missing = [orig for norm, orig in required_lower.items() if norm not in resume_lower]
    matched_preferred = [orig for norm, orig in preferred_lower.items() if norm in resume_lower]
    missing_preferred = [orig for norm, orig in preferred_lower.items() if norm not in resume_lower]

    return {
        "matched_required": matched,
        "missing_required": missing,
        "matched_preferred": matched_preferred,
        "missing_preferred": missing_preferred,
        "match_score": (len(matched) / len(job_required_skills) * 100) if job_required_skills else 0.0,
    }


def reorder_experience(
    experiences: List[Dict[str, Any]],
    job_keywords: List[str],
) -> Dict[str, Any]:
    """Score and reorder work experiences by relevance to the job.

    Args:
        experiences: List of work experience dicts (must include 'id').
        job_keywords: Keywords/skills from the job description.

    Returns:
        A dict with 'experience_order' (list of IDs) and 'relevance_scores' (id -> score).
    """
    keywords_lower = {kw.lower() for kw in job_keywords}

    scored: List[Dict[str, Any]] = []
    for exp in experiences:
        exp_id = exp.get("id", "")
        text_blob = " ".join(
            [
                exp.get("title", ""),
                exp.get("company", ""),
                exp.get("description", ""),
                " ".join(exp.get("bullet_points", [])),
                " ".join(exp.get("technologies", [])),
            ]
        ).lower()

        hits = sum(1 for kw in keywords_lower if kw in text_blob)
        score = round(hits / max(len(keywords_lower), 1) * 100, 2)
        scored.append({"id": exp_id, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)

    return {
        "experience_order": [s["id"] for s in scored],
        "relevance_scores": {s["id"]: s["score"] for s in scored},
    }


def enhance_bullet_points(
    experience_id: str,
    original_bullets: List[str],
    job_title: str,
    job_required_skills: List[str],
    llm_service: Optional[LLMService] = None,
) -> Dict[str, Any]:
    """Rewrite bullet points to better align with a target job.

    Args:
        experience_id: ID of the work experience entry.
        original_bullets: Original bullet point strings.
        job_title: Title of the target job.
        job_required_skills: Required skills from the job description.
        llm_service: LLMService instance for rewriting.

    Returns:
        A dict with 'experience_id' and 'enhanced_bullets'.
    """
    if not original_bullets:
        return {"experience_id": experience_id, "enhanced_bullets": []}

    if llm_service is None:
        return {"experience_id": experience_id, "enhanced_bullets": original_bullets}

    skills_str = ", ".join(job_required_skills[:15])
    bullets_str = "\n".join(f"- {b}" for b in original_bullets)

    prompt = (
        f"You are an expert resume writer. Rewrite the following work experience bullet points "
        f"to better match the target job: '{job_title}'.\n\n"
        f"Key required skills for the job: {skills_str}\n\n"
        f"Original bullet points:\n{bullets_str}\n\n"
        "Rules:\n"
        "- Start each bullet with a strong action verb.\n"
        "- Quantify achievements where possible (e.g. 'reduced latency by 30%').\n"
        "- Incorporate relevant keywords naturally.\n"
        "- Keep each bullet to 1-2 sentences.\n"
        "- Return ONLY a JSON array of strings, e.g. [\"Bullet 1\", \"Bullet 2\"]."
    )

    response = llm_service.generate_json(prompt)
    if isinstance(response, list):
        enhanced = [str(b) for b in response]
    elif isinstance(response, dict) and "bullets" in response:
        enhanced = [str(b) for b in response["bullets"]]
    else:
        enhanced = original_bullets

    return {"experience_id": experience_id, "enhanced_bullets": enhanced}


# ---------------------------------------------------------------------------
# ResumeTailoringAgent
# ---------------------------------------------------------------------------


class ResumeTailoringAgent:
    """Agent for tailoring resumes to job descriptions using Google ADK."""

    SYSTEM_PROMPT = (
        "You are an expert resume writer and career coach. Your task is to tailor "
        "a candidate's resume to maximise its match with a specific job description. "
        "Use the provided tools to highlight skills, reorder experiences, and enhance "
        "bullet points. Always return structured JSON."
    )

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        resume_parser: Optional[ResumeParser] = None,
        job_parser: Optional[JobParser] = None,
    ):
        """Initialise the agent with optional service dependencies."""
        self.llm_service = llm_service or LLMService()
        self.resume_parser = resume_parser or ResumeParser(llm_service=self.llm_service)
        self.job_parser = job_parser or JobParser(llm_service=self.llm_service)

        # Try to set up the ADK agent (optional; used only when available)
        self._adk_agent = None
        self._adk_runner = None
        self._adk_session_service = None
        self._setup_adk_agent()

    # ------------------------------------------------------------------
    # ADK setup
    # ------------------------------------------------------------------

    def _setup_adk_agent(self) -> None:
        """Initialise the Google ADK agent with tool functions."""
        try:
            from google.adk.agents import Agent
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService

            self._adk_session_service = InMemorySessionService()

            self._adk_agent = Agent(
                model=self.llm_service._model,
                name="resume_tailor_agent",
                instruction=self.SYSTEM_PROMPT,
                tools=[highlight_skills, reorder_experience],  # LLM-callable tools
            )

            self._adk_runner = Runner(
                agent=self._adk_agent,
                app_name="job_booster",
                session_service=self._adk_session_service,
            )
            logger.info("ResumeTailoringAgent ADK runner initialized.")
        except ImportError:
            logger.warning("google-adk not available; agent will use direct tool calls.")
        except Exception as exc:
            logger.warning(f"ADK agent setup failed (will use direct calls): {exc}")

    # ------------------------------------------------------------------
    # Core orchestration
    # ------------------------------------------------------------------

    def tailor_resume(
        self,
        resume: Resume,
        job: JobPosting,
        format_type: str = "text",
    ) -> Dict[str, Any]:
        """Tailor a resume to a job description.

        Args:
            resume: Parsed Resume Pydantic object.
            job: Parsed JobPosting Pydantic object.
            format_type: Desired output format: text | html | pdf | docx.

        Returns:
            Dict with keys: tailored_content, improvements, match_score,
            matched_skills, missing_skills, experience_order.
        """
        logger.info(f"Tailoring resume for job: {job.title!r} (format: {format_type})")

        # 1. Collect resume skills
        resume_skills = [s.name for s in (resume.skills or [])]
        job_required = job.required_skills or []
        job_preferred = job.preferred_skills or []
        job_keywords: List[str] = list({*job_required, *job_preferred, *(job.keywords or [])})

        # 2. Highlight skills
        skill_result = highlight_skills(resume_skills, job_required, job_preferred)

        # 3. Reorder experiences
        exp_dicts = [exp.model_dump() for exp in (resume.work_experience or [])]
        reorder_result = reorder_experience(exp_dicts, job_keywords)

        ordered_exp_ids: List[str] = reorder_result.get("experience_order", [])
        relevance_scores: Dict[str, float] = reorder_result.get("relevance_scores", {})

        # 4. Enhance bullet points for each experience
        enhanced_bullets_map: Dict[str, List[str]] = {}
        exp_by_id = {exp.id: exp for exp in (resume.work_experience or [])}

        for exp_id in ordered_exp_ids:
            exp = exp_by_id.get(exp_id)
            if exp is None:
                continue
            result = enhance_bullet_points(
                experience_id=exp_id,
                original_bullets=exp.bullet_points or [],
                job_title=job.title or "",
                job_required_skills=job_required,
                llm_service=self.llm_service,
            )
            enhanced_bullets_map[exp_id] = result.get("enhanced_bullets", exp.bullet_points or [])

        # 5. Generate the tailored resume text
        tailored_content = self._generate_tailored_content(
            resume=resume,
            job=job,
            ordered_exp_ids=ordered_exp_ids,
            enhanced_bullets_map=enhanced_bullets_map,
            skill_result=skill_result,
            format_type=format_type,
        )

        # 6. Collect improvements
        improvements = self._collect_improvements(skill_result, enhanced_bullets_map, exp_by_id)

        return {
            "tailored_content": tailored_content,
            "improvements": improvements,
            "match_score": skill_result.get("match_score", 0.0),
            "matched_skills": skill_result.get("matched_required", []),
            "missing_skills": skill_result.get("missing_required", []),
            "experience_order": ordered_exp_ids,
            "relevance_scores": relevance_scores,
        }

    def generate_tailored_resume(
        self,
        resume_data: Dict[str, Any],
        job_data: Dict[str, Any],
        format_type: str = "text",
    ) -> Dict[str, Any]:
        """Generate a tailored resume from arbitrary data dicts.

        Accepts raw dicts (e.g. from the API or frontend) and converts them
        to Resume/JobPosting objects before calling tailor_resume.

        Args:
            resume_data: Resume data as a plain dict.
            job_data: Job description data as a plain dict.
            format_type: Desired output format.

        Returns:
            Same dict structure as tailor_resume.
        """
        try:
            resume = Resume(**resume_data) if resume_data else Resume()
        except Exception as exc:
            logger.warning(f"Could not construct Resume from dict: {exc}. Using empty Resume.")
            resume = Resume()

        try:
            job = JobPosting(**job_data) if job_data else JobPosting()
        except Exception as exc:
            logger.warning(f"Could not construct JobPosting from dict: {exc}. Using empty JobPosting.")
            job = JobPosting()

        return self.tailor_resume(resume=resume, job=job, format_type=format_type)

    # ------------------------------------------------------------------
    # Content generation helpers
    # ------------------------------------------------------------------

    def _generate_tailored_content(
        self,
        resume: Resume,
        job: JobPosting,
        ordered_exp_ids: List[str],
        enhanced_bullets_map: Dict[str, List[str]],
        skill_result: Dict[str, Any],
        format_type: str,
    ) -> str:
        """Ask the LLM to produce the final tailored resume text."""
        # Build a structured representation to pass to the LLM
        exp_by_id = {exp.id: exp for exp in (resume.work_experience or [])}

        ordered_experiences = []
        for exp_id in ordered_exp_ids:
            exp = exp_by_id.get(exp_id)
            if exp is None:
                continue
            exp_dict = exp.model_dump()
            exp_dict["bullet_points"] = enhanced_bullets_map.get(exp_id, exp.bullet_points or [])
            ordered_experiences.append(exp_dict)

        resume_snapshot = {
            "contact": resume.contact.model_dump() if resume.contact else {},
            "summary": resume.summary,
            "work_experience": ordered_experiences,
            "education": [e.model_dump() for e in (resume.education or [])],
            "skills": [s.model_dump() for s in (resume.skills or [])],
            "projects": [p.model_dump() for p in (resume.projects or [])],
            "certifications": [c.model_dump() for c in (resume.certifications or [])],
            "languages": resume.languages or [],
            "awards": resume.awards or [],
        }

        job_snapshot = {
            "title": job.title,
            "company": job.company.model_dump() if job.company else {},
            "required_skills": job.required_skills,
            "responsibilities": [r.description for r in (job.responsibilities or [])],
        }

        matched_skills = skill_result.get("matched_required", [])

        format_instructions = {
            "text": "plain text with clear section headers and bullet points",
            "html": "well-structured HTML with <h2> section headers and <ul>/<li> bullet points",
            "pdf": "well-formatted text ready for PDF conversion (plain text with clear structure)",
            "docx": "plain text with clear section headers, ready for DOCX conversion",
        }.get(format_type.lower(), "plain text")

        prompt = (
            f"You are a professional resume writer. Using the structured resume data and job info below, "
            f"write a complete, tailored resume in {format_instructions}.\n\n"
            f"Focus on highlighting: {', '.join(matched_skills[:10]) if matched_skills else 'all relevant skills'}.\n\n"
            f"Resume data:\n{json.dumps(resume_snapshot, indent=2, default=str)}\n\n"
            f"Target job:\n{json.dumps(job_snapshot, indent=2, default=str)}\n\n"
            "Output ONLY the resume content, nothing else."
        )

        content = self.llm_service.generate_text(prompt)
        if not content:
            # Fallback: render a basic text resume without LLM
            content = self._render_basic_resume(resume, ordered_exp_ids, enhanced_bullets_map)

        return content

    @staticmethod
    def _render_basic_resume(
        resume: Resume,
        ordered_exp_ids: List[str],
        enhanced_bullets_map: Dict[str, List[str]],
    ) -> str:
        """Fallback plain-text renderer when the LLM is unavailable."""
        lines: List[str] = []

        if resume.contact:
            c = resume.contact
            lines.append(c.name or "")
            if c.email:
                lines.append(c.email)
            if c.phone:
                lines.append(c.phone)
            if c.location:
                lines.append(c.location)
            lines.append("")

        if resume.summary:
            lines += ["SUMMARY", "-------", resume.summary, ""]

        if resume.work_experience:
            lines += ["EXPERIENCE", "----------"]
            exp_by_id = {exp.id: exp for exp in resume.work_experience}
            for exp_id in ordered_exp_ids:
                exp = exp_by_id.get(exp_id)
                if exp is None:
                    continue
                date_range = f"{exp.start_date or ''} - {exp.end_date or 'Present'}"
                lines.append(f"{exp.title} | {exp.company} | {date_range}")
                for bullet in enhanced_bullets_map.get(exp_id, exp.bullet_points or []):
                    lines.append(f"  • {bullet}")
                lines.append("")

        if resume.education:
            lines += ["EDUCATION", "---------"]
            for edu in resume.education:
                lines.append(f"{edu.degree or ''} in {edu.field_of_study or ''} — {edu.institution}")
                if edu.end_date:
                    lines.append(f"  Graduated: {edu.end_date}")
                lines.append("")

        if resume.skills:
            lines += ["SKILLS", "------"]
            skill_names = [s.name for s in resume.skills]
            lines.append(", ".join(skill_names))
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Improvements extraction
    # ------------------------------------------------------------------

    def _collect_improvements(
        self,
        skill_result: Dict[str, Any],
        enhanced_bullets_map: Dict[str, List[str]],
        exp_by_id: Dict[str, Any],
    ) -> List[str]:
        """Build a human-readable list of improvements made."""
        improvements: List[str] = []

        matched = skill_result.get("matched_required", [])
        missing = skill_result.get("missing_required", [])
        match_score = skill_result.get("match_score", 0.0)

        improvements.append(f"Skill match score: {match_score:.1f}%")

        if matched:
            improvements.append(f"Highlighted {len(matched)} matching skills: {', '.join(matched[:5])}")

        if missing:
            improvements.append(
                f"Note: {len(missing)} required skills not found in resume: {', '.join(missing[:5])}"
            )

        bullet_count = sum(len(v) for v in enhanced_bullets_map.values())
        if bullet_count:
            improvements.append(
                f"Enhanced bullet points for {len(enhanced_bullets_map)} work experience entries "
                f"({bullet_count} bullets total)."
            )

        if exp_by_id:
            improvements.append(
                f"Reordered {len(exp_by_id)} work experience entries by relevance to the job."
            )

        return improvements

    # ------------------------------------------------------------------
    # Analysis (standalone helper)
    # ------------------------------------------------------------------

    def analyze_match(self, resume: Resume, job: JobPosting) -> Dict[str, Any]:
        """Analyse how well a resume matches a job description.

        Returns a comprehensive analysis dict including match score,
        skill gaps, strengths, and recommendations.
        """
        resume_skills = [s.name for s in (resume.skills or [])]
        job_required = job.required_skills or []
        job_preferred = job.preferred_skills or []
        job_keywords: List[str] = list({*job_required, *job_preferred, *(job.keywords or [])})

        skill_result = highlight_skills(resume_skills, job_required, job_preferred)

        exp_dicts = [exp.model_dump() for exp in (resume.work_experience or [])]
        reorder_result = reorder_experience(exp_dicts, job_keywords)

        # Ask LLM for qualitative analysis
        analysis_prompt = (
            "Analyse the fit between the following resume and job description. "
            "Return a JSON object with keys: strengths (list), gaps (list), "
            "recommendations (list).\n\n"
            f"Resume skills: {resume_skills}\n"
            f"Job required skills: {job_required}\n"
            f"Matched skills: {skill_result.get('matched_required', [])}\n"
            f"Missing skills: {skill_result.get('missing_required', [])}\n"
            f"Job responsibilities: {[r.description for r in (job.responsibilities or [])][:5]}"
        )
        qualitative = self.llm_service.generate_json(analysis_prompt)

        return {
            "match_score": skill_result.get("match_score", 0.0),
            "matched_skills": skill_result.get("matched_required", []),
            "missing_skills": skill_result.get("missing_required", []),
            "matched_preferred": skill_result.get("matched_preferred", []),
            "experience_order": reorder_result.get("experience_order", []),
            "relevance_scores": reorder_result.get("relevance_scores", {}),
            "strengths": qualitative.get("strengths", []),
            "gaps": qualitative.get("gaps", []),
            "recommendations": qualitative.get("recommendations", []),
        }
