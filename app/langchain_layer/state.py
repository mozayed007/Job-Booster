"""LangGraph state definition for the LangChain AI layer."""

from dataclasses import dataclass, field
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


@dataclass
class LCGraphState:
    """Shared state passed through a LangGraph pipeline.

    This dataclass mirrors the existing ``PipelineState`` so the two layers can
    be compared directly. Artifacts accumulate keyed by agent name, exactly like
    the Pydantic AI pipeline engine.
    """

    # Inputs
    pipeline_name: str = ""
    resume_text: str = ""
    job_text: str = ""
    cv_text: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)

    # LangGraph message history (reducer handles append semantics)
    messages: Annotated[list[BaseMessage], add_messages] = field(default_factory=list)

    # Outputs
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    current_step: int = 0

    def get_resume_text(self) -> str:
        """Return the best available resume text, mirroring PipelineState."""
        for key, attr in [
            ("resume_reviewer", "full_rewritten_resume"),
            ("cv_extractor", "tailored_resume"),
            ("resume_tailor", "tailored_content"),
        ]:
            artifact = self.artifacts.get(key)
            if artifact and getattr(artifact, attr, None):
                value = getattr(artifact, attr)
                return str(value)
        return self.cv_text or self.resume_text
