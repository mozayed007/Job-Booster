"""Cover Letter Generation Agent."""

from typing import cast

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.pipelines.state import PipelineState


class CoverLetterOutput(BaseModel):
    """Output from the cover letter generator."""

    cover_letter: str
    key_highlights: list[str] = Field(default_factory=list)
    tone: str = "professional"


class CoverLetterAgent(BaseAgent):
    """Generates tailored cover letters from resume and job description."""

    output_type = CoverLetterOutput

    async def execute(self, state: PipelineState) -> None:
        """Pipeline integration: generate cover letter and store in artifacts."""
        result = await self.generate(state.get_resume_text(), state.job_text)
        state.artifacts["cover_letter_generator"] = result

    async def generate(
        self,
        resume_text: str,
        job_text: str,
        company_name: str | None = None,
        hiring_manager: str | None = None,
    ) -> CoverLetterOutput:
        """Generate a cover letter.

        Args:
            resume_text: The candidate's resume text
            job_text: The job description text
            company_name: Optional company name for personalization
            hiring_manager: Optional hiring manager name

        Returns:
            CoverLetterOutput with generated letter and highlights
        """
        if not self._agent:
            return CoverLetterOutput(
                cover_letter="Error: Cover letter agent not available.",
                key_highlights=[],
                tone="professional",
            )

        prompt = self._build_prompt(resume_text, job_text, company_name, hiring_manager)

        try:
            result = await self._agent.run(prompt)
            return cast(CoverLetterOutput, result.output)
        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            return CoverLetterOutput(
                cover_letter=f"Error generating cover letter: {e}",
                key_highlights=[],
                tone="professional",
            )

    def _build_prompt(
        self,
        resume_text: str,
        job_text: str,
        company_name: str | None,
        hiring_manager: str | None,
    ) -> str:
        """Build the user prompt for cover letter generation."""
        parts = [
            "Generate a tailored cover letter based on the following resume and job description.",
            "",
            "## Resume",
            resume_text[:6000],
            "",
            "## Job Description",
            job_text[:4000],
        ]

        if company_name:
            parts.append(f"\nCompany: {company_name}")
        if hiring_manager:
            parts.append(f"Hiring Manager: {hiring_manager}")

        return "\n".join(parts)


async def generate_cover_letter(
    resume_text: str,
    job_text: str,
    company_name: str | None = None,
    hiring_manager: str | None = None,
) -> CoverLetterOutput:
    """Convenience function: generate a cover letter.

    Args:
        resume_text: The candidate's resume text
        job_text: The job description text
        company_name: Optional company name
        hiring_manager: Optional hiring manager name

    Returns:
        CoverLetterOutput with generated letter and highlights
    """
    from app.agents.base_agent import get_agent

    agent = get_agent("cover_letter_generator")
    if agent is None:
        return CoverLetterOutput(
            cover_letter="Error: Cover letter agent not available.",
            key_highlights=[],
            tone="professional",
        )

    return await cast(CoverLetterAgent, agent).generate(
        resume_text, job_text, company_name, hiring_manager
    )
