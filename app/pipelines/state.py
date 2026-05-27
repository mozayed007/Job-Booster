"""Pipeline state management."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PipelineState:
    """State passed through pipeline execution.
    
    Inputs are set at pipeline start. Outputs are accumulated in artifacts
    as each agent executes.
    """
    
    # Inputs (set at construction)
    pipeline_name: str = ""
    resume_text: str = ""
    job_text: str = ""
    cv_text: str = ""
    
    # Outputs (populated by agents)
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    current_step: int = 0
    
    def get_resume_text(self) -> str:
        """Get the best available resume text from artifacts or inputs.
        
        Priority order:
        1. Resume reviewer output (most refined)
        2. CV extractor output (tailored)
        3. Resume tailor output (tailored)
        4. Raw input (cv_text or resume_text)
        """
        # Check artifacts in priority order
        for key, attr in [
            ("resume_reviewer", "full_rewritten_resume"),
            ("cv_extractor", "tailored_resume"),
            ("resume_tailor", "tailored_content"),
        ]:
            artifact = self.artifacts.get(key)
            if artifact and getattr(artifact, attr, None):
                return getattr(artifact, attr)
        
        # Fall back to raw input
        return self.cv_text or self.resume_text
