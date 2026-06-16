"""LangGraph pipeline engine that mirrors ``app.pipelines.engine``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import yaml
from langgraph.graph import END, START, StateGraph
from loguru import logger

from app.langchain_layer.agents import AGENT_REGISTRY, LangChainAgent, build_agent
from app.langchain_layer.factory import build_llm
from app.langchain_layer.state import LCGraphState
from app.langchain_layer.tools import get_lc_tools_for_agent

PipelineStepFn = Callable[[LCGraphState], Awaitable[LCGraphState]]


class PipelineStep:
    """A single step in a LangGraph pipeline, bound to a LangChain agent."""

    def __init__(self, agent_key: str, description: str = ""):
        self.agent_key = agent_key
        self.description = description


class LangGraphPipelineConfig:
    """Configuration for a single LangGraph pipeline."""

    def __init__(
        self,
        name: str,
        description: str = "",
        enabled: bool = True,
        steps: list[PipelineStep] | None = None,
    ):
        self.name = name
        self.description = description
        self.enabled = enabled
        self.steps = steps or []


_PIPELINES_YAML = Path(__file__).resolve().parent.parent / "pipelines" / "pipelines.yaml"
_configs: dict[str, LangGraphPipelineConfig] = {}


def load_pipeline_configs(yaml_path: Path | None = None) -> dict[str, LangGraphPipelineConfig]:
    """Load pipeline definitions from the same YAML file used by PipelineEngine."""
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
            if s["agent"] in AGENT_REGISTRY
        ]

        configs[key] = LangGraphPipelineConfig(
            name=cfg.get("name", key),
            description=cfg.get("description", ""),
            enabled=cfg.get("enabled", True),
            steps=steps,
        )

    _configs = configs
    return _configs


def get_pipeline_config(name: str) -> LangGraphPipelineConfig | None:
    """Get a loaded pipeline config by key."""
    if not _configs:
        load_pipeline_configs()
    return _configs.get(name)


def _make_node(agent_key: str, agent: LangChainAgent) -> PipelineStepFn:
    """Create a LangGraph node function that runs a single agent."""

    async def _node(state: LCGraphState) -> LCGraphState:
        return await agent.execute(state)

    _node.__name__ = agent_key
    return _node


def build_pipeline_graph(
    pipeline_key: str,
    model: Any | None = None,
) -> Any:
    """Build a compiled LangGraph for a pipeline defined in ``pipelines.yaml``.

    Args:
        pipeline_key: Pipeline key from ``pipelines.yaml``.
        model: Optional chat model to share across agents.

    Returns:
        A compiled ``StateGraph`` ready for ``ainvoke``.
    """
    config = get_pipeline_config(pipeline_key)
    if config is None:
        raise ValueError(f"Pipeline '{pipeline_key}' not found or has no LangChain agents")

    shared_model = model or build_llm()
    workflow = StateGraph(LCGraphState)

    previous_node: str | None = None
    for step in config.steps:
        agent_tools = get_lc_tools_for_agent(step.agent_key)
        agent = build_agent(step.agent_key, model=shared_model, tools=agent_tools)
        if agent is None:
            logger.warning(f"Skipping unknown agent '{step.agent_key}' in pipeline")
            continue

        node_fn = _make_node(step.agent_key, agent)
        workflow.add_node(step.agent_key, node_fn)  # type: ignore[call-overload]

        if previous_node is None:
            workflow.add_edge(START, step.agent_key)
        else:
            workflow.add_edge(previous_node, step.agent_key)
        previous_node = step.agent_key

    if previous_node is None:
        # No runnable agents: start -> end
        workflow.add_edge(START, END)
    else:
        workflow.add_edge(previous_node, END)

    return workflow.compile()


class LangGraphPipeline:
    """High-level runner for LangGraph pipelines.

    Mirrors ``PipelineEngine`` from ``app.pipelines.engine`` so callers can swap
    between Pydantic AI and LangChain implementations with minimal changes.
    """

    def __init__(self):
        if not _configs:
            load_pipeline_configs()

    async def run(
        self,
        pipeline_key: str,
        resume_text: str = "",
        job_text: str = "",
        cv_text: str = "",
        inputs: dict[str, Any] | None = None,
    ) -> LCGraphState:
        """Run a LangGraph pipeline end-to-end.

        Args:
            pipeline_key: Pipeline key from ``pipelines.yaml``.
            resume_text: Raw resume text.
            job_text: Job description text.
            cv_text: Raw CV text (alternative to resume_text).
            inputs: Extra inputs for specific agents (company_name, etc.).

        Returns:
            Final ``LCGraphState`` with accumulated artifacts.
        """
        config = get_pipeline_config(pipeline_key)
        if config is None:
            return LCGraphState(
                pipeline_name=pipeline_key,
                errors=[f"Pipeline '{pipeline_key}' not found"],
            )

        graph = build_pipeline_graph(pipeline_key)
        initial_state = LCGraphState(
            pipeline_name=config.name,
            resume_text=resume_text,
            job_text=job_text,
            cv_text=cv_text,
            inputs=inputs or {},
            messages=[],
            artifacts={},
            errors=[],
            current_step=0,
        )

        try:
            from app.core.langfuse_setup import get_langfuse_handler

            handler = get_langfuse_handler()
            lc_config = {"callbacks": [handler]} if handler else None
            final_state = await graph.ainvoke(initial_state, config=lc_config)
            # LangGraph may return a plain dict even when the schema is a dataclass.
            if isinstance(final_state, dict):
                return LCGraphState(**final_state)
            return final_state
        except Exception as exc:
            logger.error(f"LangGraph pipeline '{pipeline_key}' failed: {exc}")
            return LCGraphState(
                pipeline_name=config.name,
                resume_text=resume_text,
                job_text=job_text,
                cv_text=cv_text,
                inputs=inputs or {},
                messages=[],
                artifacts={},
                errors=[f"Pipeline execution failed: {exc}"],
                current_step=0,
            )


_engine: LangGraphPipeline | None = None


def get_engine() -> LangGraphPipeline:
    """Return the singleton LangGraph pipeline runner."""
    global _engine
    if _engine is None:
        _engine = LangGraphPipeline()
    return _engine


async def run_pipeline(
    pipeline_key: str,
    resume_text: str = "",
    job_text: str = "",
    cv_text: str = "",
    inputs: dict[str, Any] | None = None,
) -> LCGraphState:
    """Convenience function: run a LangGraph pipeline by key."""
    return await get_engine().run(
        pipeline_key,
        resume_text=resume_text,
        job_text=job_text,
        cv_text=cv_text,
        inputs=inputs or {},
    )
