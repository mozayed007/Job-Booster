"""CV Extractor Agent — extracts and tailors CV content to job descriptions."""

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.pipelines.state import PipelineState


class CVExtractorOutput(BaseModel):
    """Output from the CV extractor."""
    
    tailored_resume: str
    improvements: list[str] = Field(default_factory=list)
    relevance_summary: dict[str, list[str]] = Field(default_factory=dict)
    missing_metrics: list[str] = Field(default_factory=list)


class CvExtractorAgent(BaseAgent):
    """Extracts CV content and tailors it to job descriptions."""
    
    output_type = CVExtractorOutput
    
    async def execute(self, state: PipelineState) -> None:
        """Pipeline integration: extract and tailor CV, store in artifacts."""
        result = await self.extract_and_tailor(
            state.cv_text or state.resume_text,
            state.job_text,
        )
        state.artifacts["cv_extractor"] = result
    
    async def extract_and_tailor(
        self,
        cv_text: str,
        job_text: str,
        output_format: str = "text",
    ) -> CVExtractorOutput:
        """Extract CV content and tailor it to a job description.
        
        Args:
            cv_text: Raw CV/resume text
            job_text: Job description text
            output_format: Output format (text, markdown, etc.)
            
        Returns:
            CVExtractorOutput with tailored resume and analysis
        """
        if not self._agent:
            return CVExtractorOutput(
                tailored_resume="Error: CV extractor agent not available.",
                improvements=[],
                relevance_summary={},
                missing_metrics=[],
            )
        
        prompt = self._build_prompt(cv_text, job_text, output_format)
        
        try:
            result = await self._agent.run(prompt)
            return result.output
        except Exception as e:
            logger.error(f"CV extraction failed: {e}")
            return CVExtractorOutput(
                tailored_resume=f"Error extracting CV: {e}",
                improvements=[],
                relevance_summary={},
                missing_metrics=[],
            )
    
    def _build_prompt(self, cv_text: str, job_text: str, output_format: str) -> str:
        """Build the user prompt for CV extraction and tailoring."""
        return f"""Extract and tailor the following CV to match the job description.

## CV
{cv_text[:10000]}

## Job Description
{job_text[:5000]}

## Instructions
1. Analyze the job description for key requirements and skills
2. Identify relevant experience and skills from the CV
3. Tailor the resume to emphasize matches
4. Use the XYZ formula for bullet points where possible
5. Flag any missing metrics with [placeholder]
6. Provide a relevance summary

Output format: {output_format}
"""


async def tailor_resume_from_cv(
    cv_text: str,
    job_text: str,
    output_format: str = "text",
) -> CVExtractorOutput:
    """Convenience function: extract and tailor a CV to a job description.
    
    Args:
        cv_text: Raw CV/resume text
        job_text: Job description text
        output_format: Output format (text, markdown, etc.)
        
    Returns:
        CVExtractorOutput with tailored resume and analysis
    """
    from app.agents.base_agent import get_agent
    
    agent = get_agent("cv_extractor")
    if agent is None:
        return CVExtractorOutput(
            tailored_resume="Error: CV extractor agent not available.",
            improvements=[],
            relevance_summary={},
            missing_metrics=[],
        )
    
    return await agent.extract_and_tailor(cv_text, job_text, output_format)
