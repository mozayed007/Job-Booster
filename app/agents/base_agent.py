"""Base agent class with YAML config loading."""

from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import yaml
from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent

from app.core.model_registry import create_agent
from app.pipelines.state import PipelineState


@dataclass
class AgentConfig:
    """Configuration for a single agent, loaded from agents.yaml."""
    
    name: str
    description: str = ""
    enabled: bool = True
    skill: str | None = None
    system_prompt: str | None = None
    model_retries: int = 2
    extra: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all agents.
    
    Subclasses should:
    - Set `output_type` class attribute to their Pydantic output model
    - Implement `execute(state)` for pipeline integration
    - Implement domain-specific methods (e.g., generate(), review())
    """
    
    # Class-level output type (subclasses override this)
    output_type: ClassVar[type[BaseModel] | None] = None
    
    # Set to True if subclass creates its own agent in __init__
    _skip_base_agent: ClassVar[bool] = False
    
    def __init__(self, config: AgentConfig, base_dir: Path) -> None:
        self.config = config
        self.base_dir = base_dir
        self.skill_content = self._load_skill()
        self.system_prompt = self._load_system_prompt()
        self._agent: Agent | None = self._build_agent()
    
    def _load_skill(self) -> str:
        """Load skill markdown from file."""
        if not self.config.skill:
            return ""
        
        skill_path = self.base_dir / self.config.skill
        if not skill_path.exists():
            logger.warning(f"Skill file not found: {skill_path}")
            return ""
        
        return skill_path.read_text(encoding="utf-8")
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file, falling back to skill content."""
        if not self.config.system_prompt:
            return self.skill_content
        
        prompt_path = self.base_dir / self.config.system_prompt
        if not prompt_path.exists():
            logger.warning(f"System prompt not found: {prompt_path}")
            return self.skill_content
        
        return prompt_path.read_text(encoding="utf-8")
    
    def _resolve_output_type(self) -> type[BaseModel] | None:
        """Resolve output type from class attribute."""
        output_type = self.__class__.output_type
        if (
            output_type is not None
            and isinstance(output_type, type)
            and issubclass(output_type, BaseModel)
        ):
            return output_type
        return None
    
    def _build_agent(self) -> Agent | None:
        """Build the pydantic-ai Agent instance with optional tools."""
        if self._skip_base_agent:
            return None

        tools = getattr(self.__class__, "tools", None)

        try:
            return create_agent(
                output_type=self._resolve_output_type(),
                system_prompt=self.system_prompt,
                retries=self.config.model_retries,
                tools=tools or None,
            )
        except Exception as e:
            logger.error(f"Failed to build agent '{self.config.name}': {e}")
            return None
    
    async def execute(self, state: PipelineState) -> None:
        """Execute this agent as part of a pipeline.
        
        Subclasses must implement this to read from state inputs/artifacts
        and write results to state.artifacts.
        
        Args:
            state: Pipeline state with inputs and accumulated artifacts
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement execute()")
    
    @classmethod
    def get_instance(cls, key: str) -> "BaseAgent | None":
        """Get an agent instance from the registry.
        
        Convenience method that wraps get_agent() for use in convenience functions.
        
        Args:
            key: Agent key from agents.yaml
            
        Returns:
            Agent instance or None if not found
        """
        from app.agents.base_agent import get_agent
        return get_agent(key)


# Global registry
_AGENTS: dict[str, BaseAgent] = {}


def load_agents(
    yaml_path: Path | None = None,
    agent_filter: list[str] | None = None,
    force_reload: bool = False,
) -> dict[str, BaseAgent]:
    """Load agents from YAML configuration.
    
    Args:
        yaml_path: Path to agents.yaml (defaults to app/agents/agents.yaml)
        agent_filter: Optional list of agent keys to load (None = all)
        force_reload: Force reload even if already loaded
        
    Returns:
        Dict mapping agent keys to agent instances
    """
    global _AGENTS
    
    if _AGENTS and not force_reload:
        return _AGENTS
    
    if yaml_path is None:
        yaml_path = Path(__file__).parent / "agents.yaml"
    
    if not yaml_path.exists():
        logger.error(f"agents.yaml not found: {yaml_path}")
        return {}
    
    with open(yaml_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    agents_config = config.get("agents", {})
    base_dir = yaml_path.parent
    
    for key, agent_cfg in agents_config.items():
        if agent_filter and key not in agent_filter:
            continue
        
        if not agent_cfg.get("enabled", True):
            continue
        
        try:
            agent = _build_agent_instance(key, agent_cfg, base_dir)
            if agent:
                _AGENTS[key] = agent
        except Exception as e:
            logger.error(f"Failed to load agent '{key}': {e}")
    
    return _AGENTS


def get_agent(key: str) -> BaseAgent | None:
    """Get an agent instance by key.
    
    Args:
        key: Agent key from agents.yaml
        
    Returns:
        Agent instance or None if not found
    """
    # Load agents on first call; retry if the target agent is missing
    # (previous load may have partially failed due to transient errors).
    if not _AGENTS:
        load_agents()
    elif key not in _AGENTS:
        load_agents(force_reload=True)
    return _AGENTS.get(key)


def reload_agents() -> dict[str, BaseAgent]:
    """Force reload all agents from YAML."""
    global _AGENTS
    _AGENTS.clear()
    return load_agents(force_reload=True)


def _build_agent_instance(
    key: str,
    config: dict[str, Any],
    base_dir: Path,
) -> BaseAgent | None:
    """Build an agent instance from config.
    
    This is the canonical dispatch point mapping YAML keys to agent classes.
    """
    agent_config = AgentConfig(
        name=config.get("name", key),
        description=config.get("description", ""),
        enabled=config.get("enabled", True),
        skill=config.get("skill"),
        system_prompt=config.get("system_prompt"),
        model_retries=config.get("model_retries", 2),
        extra={
            k: v for k, v in config.items()
            if k not in (
                "name", "description", "enabled",
                "skill", "system_prompt", "model_retries",
            )
        },
    )
    
    # Dispatch to agent classes
    if key == "cover_letter_generator":
        from app.agents.cover_letter import CoverLetterAgent
        return CoverLetterAgent(agent_config, base_dir)
    
    elif key == "cv_extractor":
        from app.agents.cv_extractor import CvExtractorAgent
        return CvExtractorAgent(agent_config, base_dir)
    
    elif key == "job_finder":
        from app.agents.job_finder import JobFinderAgent
        return JobFinderAgent(agent_config, base_dir)
    
    elif key == "resume_reviewer":
        from app.agents.resume_reviewer import ResumeReviewerAgent
        return ResumeReviewerAgent(agent_config, base_dir)
    
    elif key == "resume_tailor":
        from app.agents.resume_tailor import ResumeTailorAgent
        return ResumeTailorAgent(agent_config, base_dir)
    
    elif key == "startup_scanner":
        from app.agents.startup_scanner import StartupScannerAgent
        return StartupScannerAgent(agent_config, base_dir)
    
    elif key == "outreach_agent":
        from app.agents.outreach_agent import OutreachAgent
        return OutreachAgent(agent_config, base_dir)
    
    elif key == "interview_coach":
        from app.agents.interview_coach import InterviewCoachAgent
        return InterviewCoachAgent(agent_config, base_dir)
    
    else:
        logger.warning(f"Unknown agent key: {key}")
        return None
