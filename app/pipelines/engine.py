"""Pipeline engine — orchestrates multi-agent workflows.

Loads pipeline definitions from pipelines.yaml and executes them
as sequential agent calls with shared state.
"""

from pathlib import Path

import yaml
from loguru import logger

from app.pipelines.events import EventBus
from app.pipelines.state import PipelineState


class PipelineStep:
    """A single step in a pipeline, bound to a config-driven agent."""

    def __init__(self, agent_key: str, description: str = ""):
        self.agent_key = agent_key
        self.description = description


class PipelineConfig:
    """Configuration for a single pipeline, loaded from YAML."""

    def __init__(
        self,
        name: str,
        description: str = "",
        enabled: bool = True,
        schedule: str | None = None,
        steps: list[PipelineStep] | None = None,
    ):
        self.name = name
        self.description = description
        self.enabled = enabled
        self.schedule = schedule
        self.steps = steps or []


_PIPELINES_YAML = Path(__file__).resolve().parent / "pipelines.yaml"
_configs: dict[str, PipelineConfig] = {}


def load_pipeline_configs(yaml_path: Path | None = None) -> dict[str, PipelineConfig]:
    """Load pipeline definitions from YAML."""
    global _configs

    path = yaml_path or _PIPELINES_YAML
    if not path.exists():
        logger.error(f"Pipeline config not found: {path}")
        return {}

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    configs = {}
    for key, cfg in raw.get("pipelines", {}).items():
        if not cfg.get("enabled", True):
            continue

        steps = [
            PipelineStep(
                agent_key=s["agent"],
                description=s.get("description", ""),
            )
            for s in cfg.get("steps", [])
        ]

        configs[key] = PipelineConfig(
            name=cfg.get("name", key),
            description=cfg.get("description", ""),
            enabled=cfg.get("enabled", True),
            schedule=cfg.get("schedule"),
            steps=steps,
        )

    _configs = configs
    return _configs


def get_pipeline_config(name: str) -> PipelineConfig | None:
    """Get a pipeline config by name."""
    if not _configs:
        load_pipeline_configs()
    return _configs.get(name)


class PipelineEngine:
    """Executes pipelines defined in YAML config."""

    def __init__(self):
        if not _configs:
            load_pipeline_configs()

    # ------------------------------------------------------------------
    # PipelineInputs Contract
    #
    # Each pipeline consumes specific keys from `inputs` and reads from
    # standard fields `resume_text` / `cv_text` / `job_text`.
    #
    # Pipeline          | resume() | job_text | inputs keys
    # ------------------|----------|----------|------------------------
    # full_application  | ✓        | ✓        | (none — ApplyService
    #                   |          |          |  handles company_name)
    # resume_only       | ✓        | ✓        | (none)
    # daily_scanner     | —        | —        | (none — self-contained)
    # cover_letter_only | ✓        | ✓        | (none)
    # job_search_only   | ✓        | —        | (none)
    # outreach          | ✓        | ✓        | company_name,
    #                   |          |          | hiring_manager,
    #                   |          |          | days_since_application,
    #                   |          |          | interview_stage
    # interview_prep    | ✓        | ✓(opt)   | role_type
    #
    # Standard fields:
    #   resume_text  — raw resume / CV text (input)
    #   cv_text      — alternative to resume_text (cv_extractor prefers this)
    #   job_text     — job description text
    # resume() = state.get_resume_text() — prioritized artifact fallback
    #
    # Agents that read from state.inputs:
    #   outreach_agent    → company_name, hiring_manager, days_since_application, interview_stage
    #   interview_coach   → role_type
    #
    # Agents that read from state directly:
    #   cv_extractor      → state.cv_text or state.resume_text, state.job_text
    #   resume_reviewer   → state.get_resume_text(), state.job_text
    #   resume_tailor     → state.resume_text, state.job_text
    #   cover_letter      → state.get_resume_text(), state.job_text
    #   job_finder        → state.get_resume_text()
    #   startup_scanner   → (none — fully self-contained)
    # ------------------------------------------------------------------

    async def run(
        self,
        pipeline_key: str,
        resume_text: str = "",
        job_text: str = "",
        cv_text: str = "",
        inputs: dict[str, str | int | None] | None = None,
    ) -> PipelineState:
        """Execute a pipeline end-to-end.

        See PipelineInputs Contract above for required inputs per pipeline.

        Args:
            pipeline_key: Pipeline key from pipelines.yaml
            resume_text: Raw resume text (input)
            job_text: Job description text (input)
            cv_text: Raw CV text (input, alternative to resume_text)
            inputs: Extra inputs per pipeline contract (company_name,
                    hiring_manager, days_since_application, interview_stage,
                    role_type).

        Returns:
            PipelineState with accumulated artifacts and errors
        """
        config = _configs.get(pipeline_key)
        if not config:
            raise ValueError(f"Pipeline '{pipeline_key}' not found")

        state = PipelineState(
            pipeline_name=config.name,
            resume_text=resume_text,
            job_text=job_text,
            cv_text=cv_text,
            inputs=inputs or {},
        )

        EventBus.emit(
            "pipeline_started",
            {
                "pipeline": config.name,
                "steps": len(config.steps),
            },
        )

        from app.agents import get_agent, load_agents

        load_agents()

        for i, step in enumerate(config.steps):
            state.current_step = i

            agent = get_agent(step.agent_key)
            if agent is None:
                msg = f"Agent '{step.agent_key}' not found"
                logger.error(msg)
                state.errors.append(msg)
                break

            try:
                await agent.execute(state)
            except Exception as e:
                msg = f"Step '{step.agent_key}' failed: {e}"
                logger.error(msg)
                state.errors.append(msg)
                break

            EventBus.emit(
                "step_complete",
                {
                    "pipeline": config.name,
                    "step": step.agent_key,
                    "step_index": i,
                },
            )

        EventBus.emit(
            "pipeline_completed",
            {
                "pipeline": config.name,
                "steps_completed": state.current_step + 1,
                "errors": state.errors,
            },
        )

        return state


_engine: PipelineEngine | None = None


def get_engine() -> PipelineEngine:
    """Get the singleton pipeline engine."""
    global _engine
    if _engine is None:
        _engine = PipelineEngine()
    return _engine


async def run_pipeline(
    pipeline_key: str,
    resume_text: str = "",
    job_text: str = "",
    cv_text: str = "",
    inputs: dict[str, str | int | None] | None = None,
) -> PipelineState:
    """Convenience function: run a pipeline by key.

    Args:
        pipeline_key: Pipeline key from pipelines.yaml
        resume_text: Raw resume text
        job_text: Job description text
        cv_text: Raw CV text
        inputs: Optional extra inputs for pipeline steps

    Returns:
        PipelineState with accumulated artifacts and errors
    """
    return await get_engine().run(pipeline_key, resume_text, job_text, cv_text, inputs=inputs)
