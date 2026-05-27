"""Resume Reviewer Agent — reviews and rewrites resume bullets using XYZ formula."""

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.pipelines.state import PipelineState


class BulletReview(BaseModel):
    """Review of a single bullet point."""
    
    original: str
    issues: list[str] = Field(default_factory=list)
    rewritten: str = ""


class ReviewSummary(BaseModel):
    """Summary of the resume review."""
    
    health_score: int = 0
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    structural_suggestions: list[str] = Field(default_factory=list)


class ResumeReviewerOutput(BaseModel):
    """Output from the resume reviewer."""
    
    bullet_reviews: list[BulletReview] = Field(default_factory=list)
    summary: ReviewSummary = Field(default_factory=ReviewSummary)
    full_rewritten_resume: str = ""
    metric_questions: list[str] = Field(default_factory=list)


class ResumeReviewerAgent(BaseAgent):
    """Reviews and rewrites resume bullets using the XYZ formula."""
    
    output_type = ResumeReviewerOutput
    
    async def execute(self, state: PipelineState) -> None:
        """Pipeline integration: review resume and store in artifacts."""
        result = await self.review(
            state.get_resume_text(),
            state.job_text if state.job_text else None,
        )
        state.artifacts["resume_reviewer"] = result
    
    async def review(
        self,
        resume_text: str,
        job_description: str | None = None,
    ) -> ResumeReviewerOutput:
        """Review and rewrite resume bullet points.
        
        Args:
            resume_text: The resume text to review
            job_description: Optional job description for context
            
        Returns:
            ResumeReviewerOutput with bullet reviews, summary, and rewritten resume
        """
        if not self._agent:
            return ResumeReviewerOutput(
                bullet_reviews=[],
                summary=ReviewSummary(),
                full_rewritten_resume="Error: Resume reviewer agent not available.",
                metric_questions=[],
            )
        
        prompt = self._build_prompt(resume_text, job_description)
        
        try:
            result = await self._agent.run(prompt)
            return result.output
        except Exception as e:
            logger.error(f"Resume review failed: {e}")
            return ResumeReviewerOutput(
                bullet_reviews=[],
                summary=ReviewSummary(),
                full_rewritten_resume=f"Error reviewing resume: {e}",
                metric_questions=[],
            )
    
    def _build_prompt(self, resume_text: str, job_description: str | None) -> str:
        """Build the user prompt for resume review."""
        parts = [
            "Review the following resume bullets and rewrite them using the XYZ formula.",
            "",
            "## Resume",
            resume_text[:8000],
        ]
        
        if job_description:
            parts.extend([
                "",
                "## Job Description (for context)",
                job_description[:4000],
            ])
        
        parts.extend([
            "",
            "## Instructions",
            "1. Diagnose each bullet for issues (duty-focused, missing metrics, weak verbs, etc.)",
            "2. Rewrite using XYZ formula: Accomplished [X] as measured by [Y], by doing [Z]",
            "3. Use strong action verbs from the provided categories",
            "4. Flag missing metrics with [placeholder] and suggest questions",
            "5. Provide overall health score (1-10) and summary",
        ])
        
        return "\n".join(parts)


async def review_resume(
    resume_text: str,
    job_description: str | None = None,
) -> ResumeReviewerOutput:
    """Convenience function: review and rewrite resume bullets.
    
    Args:
        resume_text: The resume text to review
        job_description: Optional job description for context
        
    Returns:
        ResumeReviewerOutput with bullet reviews, summary, and rewritten resume
    """
    from app.agents.base_agent import get_agent
    
    agent = get_agent("resume_reviewer")
    if agent is None:
        return ResumeReviewerOutput(
            bullet_reviews=[],
            summary=ReviewSummary(),
            full_rewritten_resume="Error: Resume reviewer agent not available.",
            metric_questions=[],
        )
    
    return await agent.review(resume_text, job_description)
