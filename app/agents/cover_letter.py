"""Cover Letter Generation Agent — Pydantic AI Agent."""

from pathlib import Path
from typing import Optional

from loguru import logger
from pydantic import BaseModel, Field


class CoverLetterOutput(BaseModel):
    """Output from the cover letter generation agent."""

    cover_letter: str
    key_highlights: list[str] = Field(default_factory=list)
    tone: str = "professional"


def _create_cover_letter_agent():
    """Create the Pydantic AI agent for cover letter generation."""
    try:
        from app.core.model_registry import create_agent

        prompt_path = Path(__file__).parent.parent / "prompts" / "cover_letter_prompt.md"
        system_prompt = (
            prompt_path.read_text(encoding="utf-8")
            if prompt_path.exists()
            else "Generate a professional cover letter."
        )

        return create_agent(
            output_type=CoverLetterOutput,
            system_prompt=system_prompt,
        )
    except Exception as e:
        logger.error(f"Failed to create cover letter agent: {e}")
        return None


cover_letter_agent = _create_cover_letter_agent()


async def generate_cover_letter(
    resume_text: str,
    job_text: str,
    company_name: Optional[str] = None,
    hiring_manager: Optional[str] = None,
) -> CoverLetterOutput:
    """Generate a cover letter from a resume and job description.

    Args:
        resume_text: Raw resume text.
        job_text: Raw job description text.
        company_name: Target company name (optional).
        hiring_manager: Hiring manager name (optional).

    Returns:
        CoverLetterOutput with cover letter, highlights, and tone.
    """
    if not cover_letter_agent:
        logger.error("Cover letter agent not available")
        return CoverLetterOutput(
            cover_letter="Error: Cover letter agent not available. Check LLM configuration.",
            key_highlights=[],
        )

    prompt = f"""Generate a cover letter for this job application.

--- RESUME ---
{resume_text[:6000]}

--- JOB DESCRIPTION ---
{job_text[:4000]}

{f"Company: {company_name}" if company_name else ""}
{f"Hiring Manager: {hiring_manager}" if hiring_manager else ""}
"""
    try:
        result = await cover_letter_agent.run(prompt)
        return result.output
    except Exception as e:
        logger.error(f"Cover letter generation failed: {e}")
        return CoverLetterOutput(cover_letter=f"Error: {e}", key_highlights=[])
