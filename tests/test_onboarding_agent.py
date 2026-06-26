"""Tests for the Onboarding Agent."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base_agent import AgentConfig
from app.agents.onboarding import (
    PROFILE_READY_MARKER,
    OnboardingAgent,
    PersonalProfileOutput,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> AgentConfig:
    return AgentConfig(
        name="Onboarding Agent",
        description="Test onboarding agent",
        enabled=True,
        skill="onboarding-agent.md",
        system_prompt="../prompts/onboarding_prompt.md",
    )


@pytest.fixture
def base_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "app" / "agents"


@pytest.fixture
def agent(config: AgentConfig, base_dir: Path) -> OnboardingAgent:
    return OnboardingAgent(config, base_dir)


@pytest.fixture
def sample_history() -> list[dict]:
    return [
        {"role": "user", "content": "Hi, I want to get started."},
        {"role": "assistant", "content": "Great! What do you enjoy doing outside of work?"},
        {"role": "user", "content": "I love gaming and building Arduino projects."},
        {"role": "assistant", "content": "Nice! Any tech or domains you geek out on?"},
        {"role": "user", "content": "Rust and embedded systems. I like heads-on building."},
    ]


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------


class TestPersonalProfileOutput:
    def test_defaults(self):
        profile = PersonalProfileOutput()
        assert profile.hobbies == []
        assert profile.interests == []
        assert profile.free_time_activities == []
        assert profile.favorite_tech_or_domains == []
        assert profile.work_style == ""
        assert profile.short_bio == ""
        assert profile.raw_transcript == ""

    def test_populated(self):
        profile = PersonalProfileOutput(
            hobbies=["gaming", "arduino"],
            interests=["embedded systems"],
            work_style="hands-on builder",
            short_bio="A maker who loves tinkering with hardware.",
        )
        assert "gaming" in profile.hobbies
        assert profile.work_style == "hands-on builder"
        assert "maker" in profile.short_bio

    def test_isolates_personal_context_field_names(self):
        """The output model must not contain any resume-bullet fields."""
        profile = PersonalProfileOutput()
        # Ensure no field that could be mistaken for a resume bullet exists.
        assert not hasattr(profile, "experience")
        assert not hasattr(profile, "resume_bullet")
        assert not hasattr(profile, "cover_letter")


# ---------------------------------------------------------------------------
# Agent construction
# ---------------------------------------------------------------------------


class TestAgentConstruction:
    def test_loads_system_prompt(self, agent: OnboardingAgent):
        assert "Onboarding" in agent.system_prompt
        assert "hobbies" in agent.system_prompt.lower()

    def test_output_type_is_personal_profile(self, agent: OnboardingAgent):
        assert agent.output_type is PersonalProfileOutput

    def test_chat_agent_built(self, agent: OnboardingAgent):
        assert agent._chat_agent is not None

    def test_structured_agent_built(self, agent: OnboardingAgent):
        assert agent._agent is not None


# ---------------------------------------------------------------------------
# Chat turn
# ---------------------------------------------------------------------------


class TestChatTurn:
    @pytest.mark.asyncio
    async def test_returns_string(self, agent: OnboardingAgent):
        mock_result = MagicMock()
        mock_result.output = "What do you enjoy doing outside of work?"
        agent._chat_agent = MagicMock()
        agent._chat_agent.run = AsyncMock(return_value=mock_result)

        reply = await agent.chat_turn("I want to start", [])
        assert isinstance(reply, str)
        assert "enjoy" in reply.lower()

    @pytest.mark.asyncio
    async def test_ready_marker_detected(self, agent: OnboardingAgent):
        mock_result = MagicMock()
        mock_result.output = f"Great, thanks!\n{PROFILE_READY_MARKER}"
        agent._chat_agent = MagicMock()
        agent._chat_agent.run = AsyncMock(return_value=mock_result)

        reply = await agent.chat_turn("that's all", [])
        assert PROFILE_READY_MARKER in reply

    @pytest.mark.asyncio
    async def test_error_fallback(self, agent: OnboardingAgent):
        agent._chat_agent = MagicMock()
        agent._chat_agent.run = AsyncMock(side_effect=RuntimeError("boom"))

        reply = await agent.chat_turn("hello", [])
        assert "Error" in reply or "trouble" in reply.lower()


# ---------------------------------------------------------------------------
# Finalize
# ---------------------------------------------------------------------------


class TestFinalize:
    @pytest.mark.asyncio
    async def test_produces_structured_profile(self, agent: OnboardingAgent, sample_history):
        expected = PersonalProfileOutput(
            hobbies=["gaming", "arduino"],
            favorite_tech_or_domains=["rust", "embedded systems"],
            work_style="hands-on builder",
        )
        mock_result = MagicMock()
        mock_result.output = expected
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(return_value=mock_result)

        result = await agent.finalize(sample_history)
        assert isinstance(result, PersonalProfileOutput)
        assert "gaming" in result.hobbies
        assert result.work_style == "hands-on builder"

    @pytest.mark.asyncio
    async def test_empty_history_returns_empty_profile(self, agent: OnboardingAgent):
        result = await agent.finalize([])
        assert isinstance(result, PersonalProfileOutput)
        assert result.hobbies == []

    @pytest.mark.asyncio
    async def test_error_fallback_preserves_transcript(
        self, agent: OnboardingAgent, sample_history
    ):
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(side_effect=RuntimeError("boom"))

        result = await agent.finalize(sample_history)
        assert isinstance(result, PersonalProfileOutput)
        # The transcript should be preserved in the fallback.
        assert "gaming" in result.raw_transcript or len(result.raw_transcript) > 0


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    @pytest.mark.asyncio
    async def test_execute_writes_artifact(self, agent: OnboardingAgent, sample_history):
        from app.pipelines.state import PipelineState

        expected = PersonalProfileOutput(
            hobbies=["gaming"],
            short_bio="A gamer.",
        )
        mock_result = MagicMock()
        mock_result.output = expected
        agent._agent = MagicMock()
        agent._agent.run = AsyncMock(return_value=mock_result)

        state = PipelineState(pipeline_name="onboarding")
        state.inputs["onboarding_history"] = sample_history

        await agent.execute(state)
        assert "onboarding_agent" in state.artifacts
        assert isinstance(state.artifacts["onboarding_agent"], PersonalProfileOutput)
        assert len(state.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_errors_without_history(self, agent: OnboardingAgent):
        from app.pipelines.state import PipelineState

        state = PipelineState(pipeline_name="onboarding")
        await agent.execute(state)
        assert len(state.errors) == 1
        assert "onboarding_history" in state.errors[0]
        assert "onboarding_agent" not in state.artifacts


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    def test_profile_ready_marker_is_isolated_token(self):
        """The marker must be a distinctive, literal string."""
        assert PROFILE_READY_MARKER == "[PROFILE_READY]"
