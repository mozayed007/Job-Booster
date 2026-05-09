"""Resume Tailoring Agent — Pydantic AI Agent + Graph workflow."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from app.models.job_model import JobPosting
from app.models.resume_model import Resume


class TailoredResumeOutput(BaseModel):
    """Output from the resume tailoring agent."""

    tailored_content: str
    improvements: List[str] = Field(default_factory=list)
    format_type: str = "text"


@dataclass
class WorkflowState:
    """State for the resume tailoring graph workflow."""

    resume_text: str = ""
    job_text: str = ""
    resume: Optional[Resume] = None
    job: Optional[JobPosting] = None
    match_analysis: Optional[Dict[str, Any]] = None
    tailored: Optional[TailoredResumeOutput] = None


def _create_tailor_agent():
    """Create the Pydantic AI agent for resume tailoring."""
    try:
        from app.core.model_registry import create_agent

        return create_agent(
            output_type=TailoredResumeOutput,
            system_prompt="""You are an expert resume tailor. Given a resume and job description:

1. Identify skills and experiences that match the job requirements
2. Reorder and emphasize relevant experience
3. Enhance bullet points to use action verbs and quantifiable achievements
4. Add missing keywords naturally where the candidate likely has the skill
5. Maintain truthfulness — do not fabricate experience

Return the tailored resume as clean text, and list the specific improvements made.""",
        )
    except Exception as e:
        logger.error(f"Failed to create tailor agent: {e}")
        return None


tailor_agent = _create_tailor_agent()


async def tailor_resume(
    resume_text: str,
    job_text: str,
    format_type: str = "text",
) -> TailoredResumeOutput:
    """Tailor a resume to a job description.

    Args:
        resume_text: Raw resume text.
        job_text: Raw job description text.
        format_type: Output format (text, html, latex).

    Returns:
        TailoredResumeOutput with tailored content and improvements.
    """
    if not tailor_agent:
        logger.error("Tailor agent not available")
        return TailoredResumeOutput(
            tailored_content="Error: Resume tailoring agent not available. Check LLM configuration.",
            improvements=["Agent initialization failed"],
            format_type=format_type,
        )

    prompt = f"""Tailor this resume for the following job description.

Output format: {format_type}

--- RESUME ---
{resume_text[:6000]}

--- JOB DESCRIPTION ---
{job_text[:4000]}
"""

    try:
        result = await tailor_agent.run(prompt)
        output = result.output
        output.format_type = format_type
        return output
    except Exception as e:
        logger.error(f"Resume tailoring failed: {e}")
        return TailoredResumeOutput(
            tailored_content=f"Error during tailoring: {e}",
            improvements=[],
            format_type=format_type,
        )


async def run_tailor_graph(
    resume_text: str,
    job_text: str,
    format_type: str = "text",
) -> TailoredResumeOutput:
    """Run the full tailoring workflow.

    Uses the graph pattern if pydantic-graph is available,
    otherwise falls back to direct agent call.
    """
    try:
        from pydantic_graph import BaseNode, End, Graph, GraphRunContext

        @dataclass
        class ParseInput(BaseNode[WorkflowState]):
            async def run(self, ctx: GraphRunContext[WorkflowState]) -> "GenerateTailored":
                ctx.state.resume_text = resume_text
                ctx.state.job_text = job_text
                return GenerateTailored()

        @dataclass
        class GenerateTailored(BaseNode[WorkflowState]):
            async def run(self, ctx: GraphRunContext[WorkflowState]) -> "ValidateOutput":
                output = await tailor_resume(
                    ctx.state.resume_text,
                    ctx.state.job_text,
                    format_type,
                )
                ctx.state.tailored = output
                return ValidateOutput()

        @dataclass
        class ValidateOutput(BaseNode[WorkflowState, None, TailoredResumeOutput]):
            async def run(self, ctx: GraphRunContext[WorkflowState]) -> End[TailoredResumeOutput]:
                return End(ctx.state.tailored)

        tailor_graph = Graph(nodes=[ParseInput, GenerateTailored, ValidateOutput])
        state = WorkflowState()
        result = await tailor_graph.run(ParseInput(), state=state)
        return result.output

    except ImportError:
        logger.info("pydantic-graph not available, using direct agent call")
        return await tailor_resume(resume_text, job_text, format_type)
    except Exception as e:
        logger.warning(f"Graph execution failed ({e}), falling back to direct call")
        return await tailor_resume(resume_text, job_text, format_type)
