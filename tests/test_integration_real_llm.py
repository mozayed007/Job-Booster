"""Integration tests that call the real Gemini API.

These tests verify the full AI stack works end-to-end with a real API key.
They are **skipped by default** — run with ``pytest -m integration -v``.

Requirements:
    - ``GEMINI_API_KEY`` set in ``.env`` or environment
    - Network access to the Gemini API

Cost: ~6 API calls using Gemini 3.1 Flash Lite (free-tier eligible).
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

# Load .env so os.getenv sees GEMINI_API_KEY before the skip marker evaluates.
load_dotenv()

# ---------------------------------------------------------------------------
# Skip marker — auto-skip when no API key is available
# ---------------------------------------------------------------------------

requires_gemini = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="Set GEMINI_API_KEY to run integration tests",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RESUME = (
    "Jane Doe — Senior Software Engineer\n"
    "Experience:\n"
    "- Led redesign of billing service, improving reliability to 99.99%.\n"
    "- Built a real-time feature store serving 2M+ predictions/day.\n"
    "Skills: Python, FastAPI, PostgreSQL, Kubernetes, AWS, TensorFlow.\n"
)

SAMPLE_JOB = (
    "Senior ML Engineer at Example AI\n"
    "Requirements:\n"
    "- 5+ years Python and machine learning engineering\n"
    "- Experience with FastAPI, Kubernetes, and cloud platforms\n"
    "- Track record of production ML systems at scale\n"
)


@pytest.fixture
def sample_resume() -> str:
    return SAMPLE_RESUME


@pytest.fixture
def sample_job() -> str:
    return SAMPLE_JOB


# ---------------------------------------------------------------------------
# 1. Model Registry Smoke Tests (0 API calls)
# ---------------------------------------------------------------------------


@requires_gemini
@pytest.mark.integration
class TestModelRegistrySmoke:
    """Verify the model registry detects the Gemini key and resolves correctly."""

    def test_google_provider_detected(self):
        from app.core.model_registry import Provider, get_registry

        registry = get_registry()
        assert registry._is_available(Provider.GOOGLE)

    def test_model_string_is_correct(self):
        from app.core.model_registry import get_model_string

        model = get_model_string()
        assert "gemini" in model.lower()

    def test_litellm_model_string_conversion(self):
        from app.core.model_registry import get_litellm_model_string

        litellm_model = get_litellm_model_string()
        assert "/" in litellm_model
        assert "gemini" in litellm_model.lower()

    async def test_health_check_responds(self):
        from app.core.model_registry import health_check

        results = await health_check()
        google = results.get("google", {})
        assert google.get("status") == "ok", f"Health check failed: {google}"


# ---------------------------------------------------------------------------
# 2. Pydantic AI Agent Test (1 API call)
# ---------------------------------------------------------------------------


@requires_gemini
@pytest.mark.integration
class TestPydanticAIAgent:
    """Verify a Pydantic AI Agent works with the real Gemini model."""

    async def test_simple_structured_output(self):
        from pydantic import BaseModel

        from app.core.model_registry import get_model_string

        class SimpleOutput(BaseModel):
            answer: str

        from pydantic_ai import Agent

        agent = Agent(get_model_string(), output_type=SimpleOutput)
        result = await agent.run('Return JSON: {"answer": "hello"}')

        assert isinstance(result.output, SimpleOutput)
        assert len(result.output.answer) > 0


# ---------------------------------------------------------------------------
# 3. LangChain Layer Tests (2 API calls)
# ---------------------------------------------------------------------------


@requires_gemini
@pytest.mark.integration
class TestLangChainLayer:
    """Verify the LangChain / LangGraph layer works with real models."""

    async def test_chatlitellm_responds(self):
        from langchain_core.messages import HumanMessage

        from app.langchain_layer.factory import build_llm

        llm = build_llm()
        response = await llm.ainvoke([HumanMessage(content="Say OK")])

        assert response.content
        assert len(response.content) > 0

    async def test_resume_tailor_agent(self, sample_resume, sample_job):
        from app.langchain_layer.agents import LCResumeTailorAgent

        agent = LCResumeTailorAgent(
            system_prompt="You are a resume tailor. Tailor resumes to job descriptions."
        )
        result = await agent.tailor(sample_resume, sample_job)

        from app.agents.resume_tailor import TailoredResumeOutput

        assert isinstance(result, TailoredResumeOutput)
        assert len(result.tailored_content) > 0
        assert "error" not in result.tailored_content.lower()


# ---------------------------------------------------------------------------
# 4. Pipeline End-to-End Test (2 API calls)
# ---------------------------------------------------------------------------


@requires_gemini
@pytest.mark.integration
class TestPipelineEndToEnd:
    """Verify a pipeline runs end-to-end with real LLM calls."""

    async def test_resume_only_pydantic_graph(self, sample_resume, sample_job):
        from app.pipelines.graph_engine import build_pydantic_graph
        from app.pipelines.state import PipelineState

        initial_state = PipelineState(
            pipeline_name="Resume Tailoring Only",
            resume_text=sample_resume,
            job_text=sample_job,
        )

        from app.pipelines.graph_engine import _extract_pipeline_state

        graph, start_node = build_pydantic_graph("resume_only")
        run_result = await graph.run(start_node, state=initial_state)
        result = _extract_pipeline_state(run_result, initial_state)

        assert isinstance(result, PipelineState)
        assert len(result.errors) == 0, f"Pipeline errors: {result.errors}"
        assert result.current_step >= 1
        assert "cv_extractor" in result.artifacts
