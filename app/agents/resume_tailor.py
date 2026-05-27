"""Resume Tailor Agent — tailors resumes to specific job descriptions."""

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.pipelines.state import PipelineState


class TailoredResumeOutput(BaseModel):
    """Output from the resume tailor."""
    
    tailored_content: str
    improvements: list[str] = Field(default_factory=list)
    format_type: str = "text"


class ResumeTailorAgent(BaseAgent):
    """Tailors a resume to a specific job description."""
    
    output_type = TailoredResumeOutput
    
    async def execute(self, state: PipelineState) -> None:
        """Pipeline integration: tailor resume and store in artifacts."""
        result = await self.tailor(state.resume_text, state.job_text)
        state.artifacts["resume_tailor"] = result
    
    async def tailor(
        self,
        resume_text: str,
        job_text: str,
        format_type: str = "text",
    ) -> TailoredResumeOutput:
        """Tailor a resume to a job description.
        
        Args:
            resume_text: Raw resume text
            job_text: Job description text
            format_type: Output format (text, markdown, latex)
            
        Returns:
            TailoredResumeOutput with tailored content and improvements
        """
        if not self._agent:
            return TailoredResumeOutput(
                tailored_content="Error: Resume tailor agent not available.",
                improvements=[],
                format_type=format_type,
            )
        
        prompt = self._build_prompt(resume_text, job_text, format_type)
        
        try:
            result = await self._agent.run(prompt)
            output = result.output
            output.format_type = format_type
            return output
        except Exception as e:
            logger.error(f"Resume tailoring failed: {e}")
            return TailoredResumeOutput(
                tailored_content=f"Error tailoring resume: {e}",
                improvements=[],
                format_type=format_type,
            )
    
    def _build_prompt(self, resume_text: str, job_text: str, format_type: str) -> str:
        """Build the user prompt for resume tailoring."""
        return f"""Tailor the following resume to match the job description.

## Resume
{resume_text[:6000]}

## Job Description
{job_text[:4000]}

## Instructions
1. Identify key requirements and skills from the job description
2. Reorder and emphasize relevant experience
3. Enhance bullet points using the XYZ formula where possible
4. Add relevant keywords naturally
5. Maintain truthfulness — do not fabricate experience

Output format: {format_type}
"""


async def tailor_resume(
    resume_text: str,
    job_text: str,
    format_type: str = "text",
) -> TailoredResumeOutput:
    """Convenience function: tailor a resume to a job description.
    
    Args:
        resume_text: Raw resume text
        job_text: Job description text
        format_type: Output format (text, markdown, latex)
        
    Returns:
        TailoredResumeOutput with tailored content and improvements
    """
    from app.agents.base_agent import get_agent
    
    agent = get_agent("resume_tailor")
    if agent is None:
        return TailoredResumeOutput(
            tailored_content="Error: Resume tailor agent not available.",
            improvements=[],
            format_type=format_type,
        )
    
    return await agent.tailor(resume_text, job_text, format_type)



