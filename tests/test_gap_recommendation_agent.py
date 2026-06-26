"""Tests for the Gap Recommendation Agent."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base_agent import AgentConfig
from app.agents.gap_recommendation import (
    GapRecommendationAgent,
    GapRecommendationOutput,
    Recommendation,
)
from app.pipelines.state import PipelineState

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> AgentConfig:
    return AgentConfig(
        name="Gap Recommendation Agent",
        description="Test gap rec agent",
        enabled=True,
        skill="gap-recommendation.md",
        system_prompt="../prompts/gap_recommendation_prompt.md",
    )


@pytest.fixture
def base_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "app" / "agents"


@pytest.fixture
def agent(config: AgentConfig, base_dir: Path) -> GapRecommendationAgent:
    return GapRecommendationAgent(config, base_dir)


@pytest.fixture
def sample_gaps() -> list[str]:
    return ["kubernetes", "react", "elasticsearch"]


@pytest.fixture
def sample_context() -> dict:
    return {
        "hobbies": ["gaming", "arduino"],
        "interests": ["embedded systems"],
        "favorite_tech_or_domains": ["rust", "embedded systems"],
        "work_style": "hands-on builder",
        "short_bio": "A maker who loves hardware.",
    }


@pytest.fixture
def sample_recommendations() -> list[Recommendation]:
    return [
        Recommendation(
            target_gap="kubernetes",
            project_title="Run a sensor edge service on K3s on Raspberry Pi",
            project_description="Deploy a climate sensor reader as a K3s pod.",
            why_enjoyable="Maps to your Arduino hobby — deploy real hardware.",
            estimated_effort="weekend",
            type="project",
        ),
        Recommendation(
            target_gap="react",
            project_title="Build a game tracker dashboard in React",
            project_description="Use the RAWG API to track your game library.",
            why_enjoyable="You love gaming — build something you'll use.",
            estimated_effort="1 week part-time",
            type="project",
        ),
    ]


def _mock_agent_run(agent: GapRecommendationAgent, output: GapRecommendationOutput):
    """Patch the internal pydantic-ai Agent.run to return a fixed output."""
    mock_result = MagicMock()
    mock_result.output = output
    agent._agent = MagicMock()
    agent._agent.run = AsyncMock(return_value=mock_result)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class TestRecommendation:
    def test_defaults(self):
        rec = Recommendation(
            target_gap="python",
            project_title="Build X",
            project_description="Do Y",
            why_enjoyable="Because Z",
        )
        assert rec.estimated_effort == ""
        assert rec.learning_resources == []
        assert rec.type == "project"

    def test_no_resume_bullet_fields(self):
        """Recommendation must not contain any resume-bullet-style fields."""
        rec = Recommendation(
            target_gap="x", project_title="t", project_description="d", why_enjoyable="e"
        )
        assert not hasattr(rec, "resume_bullet")
        assert not hasattr(rec, "cover_letter")
        assert not hasattr(rec, "tailored_resume")


class TestGapRecommendationOutput:
    def test_defaults(self):
        out = GapRecommendationOutput()
        assert out.recommendations == []
        assert out.summary == ""
        assert out.uncovered_gaps == []


# ---------------------------------------------------------------------------
# Agent construction
# ---------------------------------------------------------------------------


class TestAgentConstruction:
    def test_loads_system_prompt(self, agent: GapRecommendationAgent):
        assert "Gap Recommendation" in agent.system_prompt or "skill gap" in (
            agent.system_prompt.lower()
        )
        assert "fabricat" in agent.system_prompt.lower()

    def test_output_type(self, agent: GapRecommendationAgent):
        assert agent.output_type is GapRecommendationOutput


# ---------------------------------------------------------------------------
# Recommend
# ---------------------------------------------------------------------------


class TestRecommend:
    @pytest.mark.asyncio
    async def test_returns_recommendations(
        self, agent, sample_gaps, sample_context, sample_recommendations
    ):
        _mock_agent_run(
            agent,
            GapRecommendationOutput(
                recommendations=sample_recommendations,
                summary="Here are some enjoyable projects.",
                uncovered_gaps=["elasticsearch"],
            ),
        )
        result = await agent.recommend(sample_gaps, sample_context)
        assert isinstance(result, GapRecommendationOutput)
        assert len(result.recommendations) == 2
        assert result.recommendations[0].target_gap == "kubernetes"
        assert "elasticsearch" in result.uncovered_gaps

    @pytest.mark.asyncio
    async def test_empty_gaps_returns_summary(self, agent):
        result = await agent.recommend([])
        assert "No skill gaps" in result.summary
        assert len(result.recommendations) == 0

    @pytest.mark.asyncio
    async def test_no_personal_context_still_works(self, agent, sample_gaps):
        _mock_agent_run(
            agent,
            GapRecommendationOutput(
                recommendations=[
                    Recommendation(
                        target_gap="kubernetes",
                        project_title="Deploy a demo app",
                        project_description="Learn K8s basics.",
                        why_enjoyable="Broadly engaging project.",
                    )
                ],
                summary="Generic recs (no personal context).",
                uncovered_gaps=["react", "elasticsearch"],
            ),
        )
        result = await agent.recommend(sample_gaps, personal_context=None)
        assert len(result.recommendations) == 1
        assert "react" in result.uncovered_gaps

    @pytest.mark.asyncio
    async def test_agent_failure_surfaces_all_gaps_as_uncovered(
        self, agent, sample_gaps, sample_context
    ):
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=RuntimeError("LLM down"))
        result = await agent.recommend(sample_gaps, sample_context)
        assert "Error" in result.summary
        assert set(result.uncovered_gaps) == set(sample_gaps)

    @pytest.mark.asyncio
    async def test_empty_llm_output_surfaces_all_gaps(self, agent, sample_gaps, sample_context):
        """If the LLM returns no recs and no uncovered, surface all gaps."""
        _mock_agent_run(agent, GapRecommendationOutput(summary="Nothing useful."))
        result = await agent.recommend(sample_gaps, sample_context)
        assert set(result.uncovered_gaps) == set(sample_gaps)


# ---------------------------------------------------------------------------
# Fabrication guardrail
# ---------------------------------------------------------------------------


class TestFabricationGuardrail:
    @pytest.mark.asyncio
    async def test_output_never_contains_resume_bullet_fields(
        self, agent, sample_gaps, sample_context, sample_recommendations
    ):
        _mock_agent_run(
            agent,
            GapRecommendationOutput(
                recommendations=sample_recommendations,
                summary="Here you go.",
            ),
        )
        result = await agent.recommend(sample_gaps, sample_context)
        # The output model must not have any field that could be a resume bullet.
        for rec in result.recommendations:
            assert not hasattr(rec, "resume_bullet")
            assert not hasattr(rec, "cover_letter")
            assert not hasattr(rec, "tailored_resume")
            # type must be learning/build material, never "resume"
            assert rec.type != "resume"

    @pytest.mark.asyncio
    async def test_honest_uncovered_gaps(self, agent, sample_gaps, sample_context):
        """If the LLM can't map a gap, it must go in uncovered_gaps honestly."""
        _mock_agent_run(
            agent,
            GapRecommendationOutput(
                recommendations=[
                    Recommendation(
                        target_gap="kubernetes",
                        project_title="K3s on Pi",
                        project_description="Deploy hardware on K3s.",
                        why_enjoyable="Arduino fan.",
                    )
                ],
                summary="Partial coverage.",
                uncovered_gaps=["react", "elasticsearch"],
            ),
        )
        result = await agent.recommend(sample_gaps, sample_context)
        # Gaps without good recs must be honestly surfaced.
        assert "react" in result.uncovered_gaps
        assert "elasticsearch" in result.uncovered_gaps
        # The one rec targets a gap that was in the input list.
        assert result.recommendations[0].target_gap in sample_gaps


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_execute_reads_state_inputs(self, agent, sample_gaps, sample_context):
        _mock_agent_run(
            agent,
            GapRecommendationOutput(
                recommendations=[
                    Recommendation(
                        target_gap="kubernetes",
                        project_title="K3s project",
                        project_description="Deploy.",
                        why_enjoyable="Arduino.",
                    )
                ],
                summary="Done.",
            ),
        )
        state = PipelineState(pipeline_name="gap_recommendation")
        state.inputs["skill_gaps"] = sample_gaps
        state.inputs["personal_context"] = sample_context
        state.inputs["job_context"] = "ML Engineer"

        await agent.execute(state)
        assert "gap_recommendation_agent" in state.artifacts
        assert isinstance(state.artifacts["gap_recommendation_agent"], GapRecommendationOutput)
        assert len(state.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_errors_without_gaps(self, agent):
        state = PipelineState(pipeline_name="gap_recommendation")
        await agent.execute(state)
        assert len(state.errors) == 1
        assert "skill_gaps" in state.errors[0]
        assert "gap_recommendation_agent" not in state.artifacts
