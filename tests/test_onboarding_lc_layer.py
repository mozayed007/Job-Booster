"""Tests for the LangChain mirror of onboarding + gap-recommendation agents."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.gap_recommendation import GapRecommendationOutput, Recommendation
from app.agents.onboarding import PROFILE_READY_MARKER, PersonalProfileOutput
from app.langchain_layer.agents import (
    AGENT_REGISTRY,
    LCGapRecommendationAgent,
    LCOnboardingAgent,
    build_agent,
)
from app.langchain_layer.prompts import (
    build_gap_recommendation_prompt,
    build_onboarding_chat_prompt,
    build_onboarding_finalize_prompt,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_onboarding_in_registry(self):
        assert "onboarding_agent" in AGENT_REGISTRY
        assert AGENT_REGISTRY["onboarding_agent"] is LCOnboardingAgent

    def test_gap_rec_in_registry(self):
        assert "gap_recommendation_agent" in AGENT_REGISTRY
        assert AGENT_REGISTRY["gap_recommendation_agent"] is LCGapRecommendationAgent

    def test_build_agent_onboarding(self):
        agent = build_agent("onboarding_agent")
        assert isinstance(agent, LCOnboardingAgent)

    def test_build_agent_gap_rec(self):
        agent = build_agent("gap_recommendation_agent")
        assert isinstance(agent, LCGapRecommendationAgent)

    def test_build_agent_unknown_returns_none(self):
        assert build_agent("not_a_real_agent") is None


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


class TestPromptBuilders:
    def test_chat_prompt_contains_marker_instruction(self):
        prompt = build_onboarding_chat_prompt("", "hello")
        assert "CHAT:" in prompt
        assert PROFILE_READY_MARKER in prompt
        assert "hello" in prompt

    def test_chat_prompt_includes_transcript(self):
        transcript = "User: I like gaming\nAssistant: Cool!"
        prompt = build_onboarding_chat_prompt(transcript, "next")
        assert "gaming" in prompt

    def test_finalize_prompt_contains_transcript(self):
        history = [
            {"role": "user", "content": "I like gaming"},
            {"role": "assistant", "content": "Nice!"},
        ]
        prompt = build_onboarding_finalize_prompt(history)
        assert "FINALIZE:" in prompt
        assert "gaming" in prompt

    def test_gap_rec_prompt_lists_gaps(self):
        gaps = ["kubernetes", "react"]
        prompt = build_gap_recommendation_prompt(gaps)
        assert "kubernetes" in prompt
        assert "react" in prompt
        assert "Skill Gaps" in prompt

    def test_gap_rec_prompt_with_personal_context(self):
        gaps = ["docker"]
        context = {"hobbies": ["gaming"], "work_style": "builder"}
        prompt = build_gap_recommendation_prompt(gaps, context)
        assert "gaming" in prompt
        assert "builder" in prompt

    def test_gap_rec_prompt_without_context(self):
        prompt = build_gap_recommendation_prompt(["docker"], personal_context=None)
        assert "No personal context" in prompt or "not completed onboarding" in prompt.lower()

    def test_gap_rec_prompt_includes_job_context(self):
        prompt = build_gap_recommendation_prompt(["docker"], job_context="ML Engineer")
        assert "ML Engineer" in prompt


# ---------------------------------------------------------------------------
# Agent behavior (mocked)
# ---------------------------------------------------------------------------


class TestLCOnboardingAgent:
    @pytest.mark.asyncio
    async def test_chat_turn_returns_string(self):
        agent = LCOnboardingAgent(system_prompt="test")
        mock_response = MagicMock()
        mock_response.content = "What do you enjoy?"
        agent.model = MagicMock()
        agent.model.ainvoke = AsyncMock(return_value=mock_response)

        reply = await agent.chat_turn("hi", [])
        assert isinstance(reply, str)
        assert "enjoy" in reply.lower()

    @pytest.mark.asyncio
    async def test_chat_turn_error_fallback(self):
        agent = LCOnboardingAgent(system_prompt="test")
        agent.model = MagicMock()
        agent.model.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))

        reply = await agent.chat_turn("hi", [])
        assert "Error" in reply or "trouble" in reply.lower()

    @pytest.mark.asyncio
    async def test_finalize_returns_profile(self):
        agent = LCOnboardingAgent(system_prompt="test")
        expected = PersonalProfileOutput(hobbies=["gaming"])
        agent._chain = AsyncMock()
        agent._chain.ainvoke = AsyncMock(return_value=expected)

        result = await agent.finalize([{"role": "user", "content": "I like gaming"}])
        assert isinstance(result, PersonalProfileOutput)
        assert "gaming" in result.hobbies

    @pytest.mark.asyncio
    async def test_finalize_empty_history(self):
        agent = LCOnboardingAgent(system_prompt="test")
        result = await agent.finalize([])
        assert isinstance(result, PersonalProfileOutput)
        assert result.hobbies == []


class TestLCGapRecommendationAgent:
    @pytest.mark.asyncio
    async def test_recommend_returns_output(self):
        agent = LCGapRecommendationAgent(system_prompt="test")
        expected = GapRecommendationOutput(
            recommendations=[
                Recommendation(
                    target_gap="kubernetes",
                    project_title="K3s project",
                    project_description="Deploy.",
                    why_enjoyable="Arduino fan.",
                )
            ],
            summary="Enjoyable recs.",
        )
        agent._chain = AsyncMock()
        agent._chain.ainvoke = AsyncMock(return_value=expected)

        result = await agent.recommend(["kubernetes"], {"hobbies": ["arduino"]})
        assert isinstance(result, GapRecommendationOutput)
        assert len(result.recommendations) == 1

    @pytest.mark.asyncio
    async def test_recommend_empty_gaps(self):
        agent = LCGapRecommendationAgent(system_prompt="test")
        result = await agent.recommend([])
        assert "No skill gaps" in result.summary

    @pytest.mark.asyncio
    async def test_recommend_surfaces_uncovered_on_empty_output(self):
        agent = LCGapRecommendationAgent(system_prompt="test")
        # LLM returns nothing useful.
        agent._chain = AsyncMock()
        agent._chain.ainvoke = AsyncMock(return_value=GapRecommendationOutput(summary="Nothing."))

        result = await agent.recommend(["docker", "kafka"])
        assert set(result.uncovered_gaps) == {"docker", "kafka"}

    @pytest.mark.asyncio
    async def test_no_resume_bullet_fields_in_output(self):
        rec = Recommendation(
            target_gap="x", project_title="t", project_description="d", why_enjoyable="e"
        )
        assert not hasattr(rec, "resume_bullet")
        assert not hasattr(rec, "cover_letter")
        assert rec.type != "resume"
