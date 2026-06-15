"""Pydantic Graph pipeline engine — pydantic-graph backend for PipelineEngine.

This module mirrors the existing sequential ``PipelineEngine`` but expresses
pipelines as a ``pydantic_graph.Graph`` of typed nodes. It is the "Pydantic
stack" counterpart to the plain async engine and the LangGraph layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from loguru import logger
from pydantic_graph import BaseNode, End, GraphBuilder, GraphRunContext, StepContext

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
) -> GraphBuilder[PipelineState, None, PipelineState].Graph:
    """Build a pydantic-graph ``Graph`` from a pipeline config.

    Args:
        pipeline_key: Key from ``pipelines.yaml``.

    Returns:
        A compiled pydantic-graph Graph ready to ``run``.
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
    node_class.run = run

    g = GraphBuilder(
        state_type=PipelineState,
        input_type=PipelineState,
        output_type=PipelineState,
    )

    g.add(g.node(node_class))

    @g.step
    async def start(
        ctx: StepContext[PipelineState, None, PipelineState],
    ) -> node_class:
        return node_class()

    g.add(g.edge_from(g.start_node).to(start))
    return g.build()


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

        graph = build_pydantic_graph(pipeline_key)

        try:
            result = await graph.run(
                inputs=initial_state,
                state=initial_state,
            )
            if isinstance(result, PipelineState):
                return result
            if isinstance(result, End):
                return result.data if isinstance(result.data, PipelineState) else initial_state
            return initial_state
        except Exception as exc:
            logger.error(f"pydantic-graph pipeline '{pipeline_key}' failed: {exc}")
            initial_state.errors.append(f"Pipeline execution failed: {exc}")
            return initial_state


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
