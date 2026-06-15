"""Tests for the pydantic-graph pipeline engine."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic_graph import End, GraphRunContext

from app.pipelines.engine import PipelineConfig, get_pipeline_config
from app.pipelines.graph_engine import (
    AgentNode,
    PydanticGraphPipelineEngine,
    build_pydantic_graph,
    run_pipeline,
)
from app.pipelines.state import PipelineState


@pytest.fixture
def sample_resume() -> str:
    return """
Jane Doe — Senior Software Engineer
Experience:
- Led redesign of billing service, improving reliability to 99.99%.
Skills: Python, FastAPI, PostgreSQL, Kubernetes, AWS.
"""


@pytest.fixture
def sample_job() -> str:
    return "Senior ML Engineer. Requires Python, Kubernetes, and ML at scale."


class TestAgentNode:
    """Test the pydantic-graph AgentNode in isolation."""

    async def test_agent_node_executes_agent(self, monkeypatch):
        state = PipelineState(pipeline_name="test", resume_text="x", job_text="y")
        mock_agent = AsyncMock()
        monkeypatch.setattr(
            "app.pipelines.graph_engine.load_agents",
            lambda: {"cv_extractor": mock_agent},
        )

        class TwoStepNode(AgentNode):
            step_keys = ["cv_extractor", "resume_reviewer"]

        node = TwoStepNode()
        result = await node.run(GraphRunContext(state=state, deps=None))

        mock_agent.execute.assert_awaited_once_with(state)
        # One step completed and another remains -> route back to the same node.
        assert isinstance(result, AgentNode)
        assert state.current_step == 1

    async def test_agent_node_returns_end_when_no_next(self, monkeypatch):
        state = PipelineState(pipeline_name="test")
        mock_agent = AsyncMock()
        monkeypatch.setattr(
            "app.pipelines.graph_engine.load_agents",
            lambda: {"cv_extractor": mock_agent},
        )

        class SingleStepNode(AgentNode):
            step_keys = ["cv_extractor"]

        node = SingleStepNode()
        result = await node.run(GraphRunContext(state=state, deps=None))

        assert isinstance(result, End)
        assert result.data is state
        assert state.current_step == 1
        assert len(state.errors) == 0

    async def test_agent_node_handles_missing_agent(self, monkeypatch):
        state = PipelineState(pipeline_name="test")
        monkeypatch.setattr(
            "app.pipelines.graph_engine.load_agents",
            lambda: {},
        )

        class MissingAgentNode(AgentNode):
            step_keys = ["missing_agent"]

        node = MissingAgentNode()
        result = await node.run(GraphRunContext(state=state, deps=None))

        assert isinstance(result, End)
        assert len(state.errors) == 1
        assert "missing_agent" in state.errors[0]


class TestPydanticGraphBuilder:
    """Test building pydantic-graph pipelines from YAML config."""

    def test_build_resume_only_graph(self):
        graph = build_pydantic_graph("resume_only")
        assert graph is not None

    def test_build_full_application_graph(self):
        graph = build_pydantic_graph("full_application")
        assert graph is not None

    def test_build_unknown_pipeline_raises(self):
        with pytest.raises(ValueError):
            build_pydantic_graph("definitely_missing")

    def test_get_pipeline_config_matches(self):
        config = get_pipeline_config("resume_only")
        assert config is not None
        assert any(step.agent_key == "cv_extractor" for step in config.steps)


class TestPydanticGraphPipelineEngine:
    """Test end-to-end execution of pydantic-graph pipelines."""

    async def test_run_resume_only_pipeline_mocked(self, sample_resume, sample_job, monkeypatch):
        """Run resume_only with mocked agents so no real LLM calls happen."""
        cv_agent = AsyncMock()
        reviewer_agent = AsyncMock()

        def fake_load_agents():
            return {
                "cv_extractor": cv_agent,
                "resume_reviewer": reviewer_agent,
            }

        monkeypatch.setattr("app.pipelines.graph_engine.load_agents", fake_load_agents)

        engine = PydanticGraphPipelineEngine()
        final_state = await engine.run(
            "resume_only",
            resume_text=sample_resume,
            job_text=sample_job,
        )

        assert isinstance(final_state, PipelineState)
        assert len(final_state.errors) == 0
        assert final_state.current_step == 2
        cv_agent.execute.assert_awaited_once()
        reviewer_agent.execute.assert_awaited_once()

    async def test_run_pipeline_not_found(self):
        result = await run_pipeline("missing_pipeline", resume_text="x")
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].lower()

    async def test_run_empty_pipeline(self):
        """A pipeline with no steps should return the input state unchanged."""
        engine = PydanticGraphPipelineEngine()
        config = PipelineConfig(name="empty", steps=[])

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr("app.pipelines.graph_engine.get_pipeline_config", lambda key: config)
        state = await engine.run("empty", resume_text="x")
        assert state.resume_text == "x"
        assert len(state.errors) == 0
        monkeypatch.undo()
