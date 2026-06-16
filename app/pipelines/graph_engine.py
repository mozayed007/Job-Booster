"""Pydantic Graph pipeline engine — pydantic-graph backend for PipelineEngine.

This module mirrors the existing sequential ``PipelineEngine`` but expresses
pipelines as a ``pydantic_graph.Graph`` of typed nodes. It is the "Pydantic
stack" counterpart to the plain async engine and the LangGraph layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from loguru import logger
from pydantic_graph import BaseNode, End, Graph, GraphRunContext, GraphRunResult

from app.agents.base_agent import BaseAgent, load_agents
from app.pipelines.engine import get_pipeline_config
from app.pipelines.state import PipelineState


@dataclass
class AgentNode(BaseNode[PipelineState, None, PipelineState]):
    """A pydantic-graph node that executes one pipeline step at a time.

    The node mutates the shared ``PipelineState`` and routes back to itself
    until every configured step has run, then returns ``End`` with the final
    state. A single base class is used because the pipeline is purely linear;
    the concrete step list and node identity are supplied per-pipeline via a
    dynamically created subclass (see :func:`build_pydantic_graph`).
    """

    step_keys: ClassVar[list[str]] = []

    async def _execute_current_step(
        self,
        ctx: GraphRunContext[PipelineState, None],
    ) -> bool:
        """Execute the agent for ``ctx.state.current_step``.

        Returns:
            ``True`` if execution should stop (error or past last step),
            ``False`` if more steps remain.
        """
        step_index = ctx.state.current_step
        step_keys = self.step_keys

        if step_index >= len(step_keys):
            return True

        key = step_keys[step_index]
        agents = load_agents()
        agent: BaseAgent | None = agents.get(key)

        if agent is None:
            msg = f"Agent '{key}' not found"
            logger.error(msg)
            ctx.state.errors.append(msg)
            return True

        try:
            await agent.execute(ctx.state)
        except Exception as exc:
            msg = f"Step '{key}' failed: {exc}"
            logger.error(msg)
            ctx.state.errors.append(msg)
            return True

        ctx.state.current_step += 1
        return ctx.state.current_step >= len(step_keys)

    async def run(
        self,
        ctx: GraphRunContext[PipelineState, None],
    ) -> AgentNode | End[PipelineState]:
        """Execute the current step and route to the next one or end."""
        finished = await self._execute_current_step(ctx)
        if finished:
            return End(ctx.state)
        return AgentNode()


def build_pydantic_graph(
    pipeline_key: str,
) -> tuple[Graph[PipelineState, None, PipelineState], AgentNode]:
    """Build a pydantic-graph ``Graph`` from a pipeline config.

    Args:
        pipeline_key: Key from ``pipelines.yaml``.

    Returns:
        A tuple of (compiled Graph, start node instance) ready to ``run``.
    """
    config = get_pipeline_config(pipeline_key)
    if config is None:
        raise ValueError(f"Pipeline '{pipeline_key}' not found")

    step_keys = [step.agent_key for step in config.steps]

    # Create a pipeline-specific subclass so the node ID is unique and the
    # step list is captured in a class attribute.
    node_class = type(
        f"AgentNode_{pipeline_key}",
        (AgentNode,),
        {"step_keys": step_keys},
    )

    async def run(self, ctx: GraphRunContext[PipelineState, None]):
        finished = await self._execute_current_step(ctx)
        if finished:
            return End(ctx.state)
        return node_class()

    run.__annotations__["return"] = node_class | End[PipelineState]
    node_class.run = run  # type: ignore[attr-defined]

    graph = Graph(
        nodes=[node_class],
        state_type=PipelineState,
        run_end_type=PipelineState,
        name=pipeline_key,
    )
    return graph, node_class()


class PydanticGraphPipelineEngine:
    """High-level runner for pydantic-graph pipelines.

    Mirrors ``PipelineEngine`` from ``app.pipelines.engine`` so callers can swap
    between the sequential engine, pydantic-graph, and LangGraph backends.
    """

    async def run(
        self,
        pipeline_key: str,
        resume_text: str = "",
        job_text: str = "",
        cv_text: str = "",
        inputs: dict[str, str | int | None] | None = None,
    ) -> PipelineState:
        """Run a pydantic-graph pipeline end-to-end.

        Args:
            pipeline_key: Pipeline key from ``pipelines.yaml``.
            resume_text: Raw resume text.
            job_text: Job description text.
            cv_text: Raw CV text.
            inputs: Extra inputs for specific agents.

        Returns:
            Final ``PipelineState`` with accumulated artifacts.
        """
        config = get_pipeline_config(pipeline_key)
        if config is None:
            return PipelineState(
                pipeline_name=pipeline_key,
                errors=[f"Pipeline '{pipeline_key}' not found"],
            )

        initial_state = PipelineState(
            pipeline_name=config.name,
            resume_text=resume_text,
            job_text=job_text,
            cv_text=cv_text,
            inputs=inputs or {},
        )

        if not config.steps:
            return initial_state

        graph, start_node = build_pydantic_graph(pipeline_key)

        try:
            run_result = await graph.run(start_node, state=initial_state)
            return _extract_pipeline_state(run_result, initial_state)
        except Exception as exc:
            logger.error(f"pydantic-graph pipeline '{pipeline_key}' failed: {exc}")
            initial_state.errors.append(f"Pipeline execution failed: {exc}")
            return initial_state


def _extract_pipeline_state(
    run_result: GraphRunResult[PipelineState, PipelineState],
    fallback: PipelineState,
) -> PipelineState:
    """Normalize pydantic-graph run results to PipelineState."""
    output = run_result.output
    if isinstance(output, PipelineState):
        return output
    if isinstance(output, End):
        data = output.data
        if isinstance(data, PipelineState):
            return data
    state = run_result.state
    if isinstance(state, PipelineState):
        return state
    return fallback


_engine: PydanticGraphPipelineEngine | None = None


def get_engine() -> PydanticGraphPipelineEngine:
    """Return the singleton pydantic-graph pipeline runner."""
    global _engine
    if _engine is None:
        _engine = PydanticGraphPipelineEngine()
    return _engine


async def run_pipeline(
    pipeline_key: str,
    resume_text: str = "",
    job_text: str = "",
    cv_text: str = "",
    inputs: dict[str, str | int | None] | None = None,
) -> PipelineState:
    """Convenience function: run a pydantic-graph pipeline by key."""
    return await get_engine().run(
        pipeline_key,
        resume_text=resume_text,
        job_text=job_text,
        cv_text=cv_text,
        inputs=inputs,
    )
