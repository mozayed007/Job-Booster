"""LangChain agents that mirror the Pydantic AI agent layer."""

from __future__ import annotations

from typing import ClassVar

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_litellm import ChatLiteLLM
from loguru import logger
from pydantic import BaseModel, ValidationError

from app.agents.cover_letter import CoverLetterOutput
from app.agents.cv_extractor import CVExtractorOutput
from app.agents.job_finder import JobFinderOutput
from app.agents.resume_reviewer import ResumeReviewerOutput
from app.agents.resume_tailor import TailoredResumeOutput
from app.langchain_layer import prompts
from app.langchain_layer.factory import build_llm
from app.langchain_layer.state import LCGraphState


class LangChainAgent:
    """Base agent for the LangChain layer.

    Subclasses define ``output_type`` and a domain method (e.g. ``extract``) that
    builds a prompt and calls ``self.run(prompt)``. Structured output is enforced
    by binding ``with_structured_output`` to the chat model once at construction.
    """

    output_type: ClassVar[type[BaseModel]]

    def __init__(
        self,
        system_prompt: str,
        output_type: type[BaseModel] | None = None,
        model: ChatLiteLLM | None = None,
        tools: list | None = None,
    ) -> None:
        self.system_prompt = system_prompt
        self._output_type = output_type or self.__class__.output_type
        self.model = model or build_llm()
        bound_model = self.model.bind_tools(tools) if tools else self.model
        self._chain = bound_model.with_structured_output(self._output_type)  # type: ignore[attr-defined]

    @property
    def is_ready(self) -> bool:
        """Return True if the model chain is configured."""
        return self._chain is not None

    async def execute(self, state: LCGraphState) -> LCGraphState:
        """Pipeline node: subclasses must override to process state."""
        raise NotImplementedError("Subclasses must implement execute()")

    async def run(self, prompt: str) -> BaseModel:
        """Execute the chain and return a validated Pydantic output model.

        On any failure, return a fallback instance of ``output_type`` populated
        with a clear error message so callers never crash.
        """
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt),
            ]
            result = await self._chain.ainvoke(messages)
            if isinstance(result, BaseModel):
                return result
            return self._output_type.model_validate(result)
        except Exception as exc:
            logger.error(f"{self.__class__.__name__} invocation failed: {exc}")
            return self._fallback_output(str(exc))

    def _fallback_output(self, error_message: str) -> BaseModel:
        """Create a minimal valid output instance after an error."""
        try:
            return self._output_type()
        except ValidationError:
            # Required fields exist; construct without validation and attach error.
            instance = self._output_type.model_construct()
            if hasattr(instance, "errors"):
                instance.errors = [error_message]
            return instance


class LCCvExtractorAgent(LangChainAgent):
    """LangChain version of the CV Extractor agent."""

    output_type = CVExtractorOutput

    async def execute(self, state: LCGraphState) -> LCGraphState:
        """Pipeline node: extract and tailor CV content."""
        result = await self.extract_and_tailor(
            state.cv_text or state.get_resume_text(),
            state.job_text,
        )
        state.artifacts["cv_extractor"] = result
        return state

    async def extract_and_tailor(
        self,
        cv_text: str,
        job_text: str,
        output_format: str = "text",
    ) -> CVExtractorOutput:
        """Extract and tailor a CV to a job description."""
        if not cv_text or not job_text:
            return CVExtractorOutput(
                tailored_resume="Error: CV and job description are required.",
            )
        prompt = prompts.build_cv_extractor_prompt(cv_text, job_text, output_format)
        output = await self.run(prompt)
        if isinstance(output, CVExtractorOutput):
            return output
        return CVExtractorOutput(tailored_resume=str(output))


class LCResumeReviewerAgent(LangChainAgent):
    """LangChain version of the Resume Reviewer agent."""

    output_type = ResumeReviewerOutput

    async def execute(self, state: LCGraphState) -> LCGraphState:
        """Pipeline node: review the current resume."""
        result = await self.review(
            state.get_resume_text(),
            state.job_text if state.job_text else None,
        )
        state.artifacts["resume_reviewer"] = result
        return state

    async def review(
        self,
        resume_text: str,
        job_description: str | None = None,
    ) -> ResumeReviewerOutput:
        """Review and rewrite resume bullets using the XYZ formula."""
        if not resume_text:
            return ResumeReviewerOutput(
                full_rewritten_resume="Error: Resume text is required.",
            )
        prompt = prompts.build_resume_reviewer_prompt(resume_text, job_description)
        output = await self.run(prompt)
        if isinstance(output, ResumeReviewerOutput):
            return output
        return ResumeReviewerOutput(full_rewritten_resume=str(output))


class LCResumeTailorAgent(LangChainAgent):
    """LangChain version of the Resume Tailor agent."""

    output_type = TailoredResumeOutput

    async def execute(self, state: LCGraphState) -> LCGraphState:
        """Pipeline node: tailor resume to job description."""
        result = await self.tailor(state.resume_text, state.job_text)
        state.artifacts["resume_tailor"] = result
        return state

    async def tailor(
        self,
        resume_text: str,
        job_text: str,
        format_type: str = "text",
    ) -> TailoredResumeOutput:
        """Tailor a resume to a job description."""
        if not resume_text or not job_text:
            return TailoredResumeOutput(
                tailored_content="Error: Resume and job description are required.",
                format_type=format_type,
            )
        prompt = prompts.build_resume_tailor_prompt(resume_text, job_text, format_type)
        output = await self.run(prompt)
        if isinstance(output, TailoredResumeOutput):
            output.format_type = format_type
            return output
        return TailoredResumeOutput(
            tailored_content=str(output),
            format_type=format_type,
        )


class LCCoverLetterAgent(LangChainAgent):
    """LangChain version of the Cover Letter Generator agent."""

    output_type = CoverLetterOutput

    async def execute(self, state: LCGraphState) -> LCGraphState:
        """Pipeline node: generate a cover letter."""
        inputs = state.inputs
        result = await self.generate(
            state.get_resume_text(),
            state.job_text,
            company_name=inputs.get("company_name"),
            hiring_manager=inputs.get("hiring_manager"),
        )
        state.artifacts["cover_letter_generator"] = result
        return state

    async def generate(
        self,
        resume_text: str,
        job_text: str,
        company_name: str | None = None,
        hiring_manager: str | None = None,
    ) -> CoverLetterOutput:
        """Generate a tailored cover letter."""
        if not resume_text or not job_text:
            return CoverLetterOutput(
                cover_letter="Error: Resume and job description are required.",
            )
        prompt = prompts.build_cover_letter_prompt(
            resume_text, job_text, company_name, hiring_manager
        )
        output = await self.run(prompt)
        if isinstance(output, CoverLetterOutput):
            return output
        return CoverLetterOutput(cover_letter=str(output))


class LCJobFinderAgent(LangChainAgent):
    """LangChain version of the Job Finder agent."""

    output_type = JobFinderOutput

    async def execute(self, state: LCGraphState) -> LCGraphState:
        """Pipeline node: find jobs matching the resume."""
        result = await self.search(state.get_resume_text())
        state.artifacts["job_finder"] = result
        return state

    async def search(
        self,
        resume_text: str,
        top_skills: list[str] | None = None,
        target_roles: list[str] | None = None,
        location_preference: str = "remote",
        seniority_level: str | None = None,
        visa_required: bool = False,
        max_results: int = 15,
    ) -> JobFinderOutput:
        """Find AI/ML job listings matching the user's profile."""
        if not resume_text:
            return JobFinderOutput(
                summary="Error: Resume text is required.",
            )
        prompt = prompts.build_job_finder_prompt(
            resume_text,
            top_skills=top_skills,
            target_roles=target_roles,
            location_preference=location_preference,
            seniority_level=seniority_level,
            visa_required=visa_required,
            max_results=max_results,
        )
        output = await self.run(prompt)
        if isinstance(output, JobFinderOutput):
            return output
        return JobFinderOutput(summary=str(output))


AGENT_REGISTRY: dict[str, type[LangChainAgent]] = {
    "cv_extractor": LCCvExtractorAgent,
    "resume_reviewer": LCResumeReviewerAgent,
    "resume_tailor": LCResumeTailorAgent,
    "cover_letter_generator": LCCoverLetterAgent,
    "job_finder": LCJobFinderAgent,
}


def build_agent(
    agent_key: str, model: ChatLiteLLM | None = None, tools: list | None = None
) -> LangChainAgent | None:
    """Factory to build a concrete LangChain agent by key.

    Args:
        agent_key: Key matching a Pydantic AI agent name.
        model: Optional pre-built chat model.
        tools: Optional list of LangChain tools to bind.

    Returns:
        A ``LangChainAgent`` subclass instance, or None if the key is unknown.
    """
    agent_cls = AGENT_REGISTRY.get(agent_key)
    if agent_cls is None:
        logger.warning(f"Unknown LangChain agent key: {agent_key}")
        return None
    return agent_cls(
        system_prompt=f"You are the {agent_cls.__name__} for a job-search assistant.",
        model=model,
        tools=tools,
    )
