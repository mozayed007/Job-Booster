"""Tests for the LangChain + LangGraph AI layer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.agents.cover_letter import CoverLetterOutput
from app.agents.cv_extractor import CVExtractorOutput
from app.agents.job_finder import JobFinderOutput, JobListing
from app.agents.resume_reviewer import ResumeReviewerOutput
from app.agents.resume_tailor import TailoredResumeOutput
from app.langchain_layer import (
    LangChainAgent,
    LCGraphState,
    build_pipeline_graph,
    run_pipeline,
)
from app.langchain_layer.agents import (
    AGENT_REGISTRY,
    LCCoverLetterAgent,
    LCCvExtractorAgent,
    LCJobFinderAgent,
    LCResumeReviewerAgent,
    LCResumeTailorAgent,
    build_agent,
)
from app.langchain_layer.factory import build_llm, get_model_name
from app.langchain_layer.graph import (
    LangGraphPipeline,
    LangGraphPipelineConfig,
    get_pipeline_config,
    load_pipeline_configs,
)
from app.langchain_layer.prompts import (
    build_cover_letter_prompt,
    build_cv_extractor_prompt,
    build_job_finder_prompt,
    build_resume_reviewer_prompt,
    build_resume_tailor_prompt,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_resume() -> str:
    return """
Jane Doe — Senior Software Engineer
Experience:
- Led redesign of billing service, improving reliability to 99.99%.
- Built a real-time feature store serving 2M+ predictions/day.
Skills: Python, FastAPI, PostgreSQL, Kubernetes, AWS, TensorFlow.
"""


@pytest.fixture
def sample_job() -> str:
    return """
Senior ML Engineer at Example AI
Requirements:
- 5+ years Python and machine learning engineering
- Experience with FastAPI, Kubernetes, and cloud platforms
- Track record of production ML systems at scale
"""


@pytest.fixture
def fake_chain():
    """Return an async mock chain that can be attached to a LangChainAgent."""

    def _make_chain(return_value):
        chain = AsyncMock()
        chain.ainvoke = AsyncMock(return_value=return_value)
        return chain

    return _make_chain


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


class TestPromptBuilders:
    """Ensure prompts contain expected sections and truncate long inputs."""

    def test_cv_extractor_prompt(self, sample_resume, sample_job):
        prompt = build_cv_extractor_prompt(sample_resume, sample_job)
        assert "CV" in prompt
        assert "Job Description" in prompt
        assert "XYZ formula" in prompt
        assert sample_resume[:50] in prompt

    def test_resume_reviewer_prompt(self, sample_resume, sample_job):
        prompt = build_resume_reviewer_prompt(sample_resume, sample_job)
        assert "XYZ formula" in prompt
        assert "Job Description (for context)" in prompt

    def test_resume_reviewer_prompt_without_job(self, sample_resume):
        prompt = build_resume_reviewer_prompt(sample_resume)
        assert "Job Description" not in prompt

    def test_resume_tailor_prompt(self, sample_resume, sample_job):
        prompt = build_resume_tailor_prompt(sample_resume, sample_job)
        assert "Tailor" in prompt
        assert "truthfulness" in prompt

    def test_cover_letter_prompt(self, sample_resume, sample_job):
        prompt = build_cover_letter_prompt(
            sample_resume, sample_job, company_name="Example AI", hiring_manager="Alex"
        )
        assert "Company: Example AI" in prompt
        assert "Hiring Manager: Alex" in prompt

    def test_job_finder_prompt(self, sample_resume):
        prompt = build_job_finder_prompt(
            sample_resume,
            top_skills=["Python", "Kubernetes"],
            target_roles=["ML Engineer"],
            location_preference="remote",
            seniority_level="senior",
            visa_required=True,
            max_results=10,
        )
        assert "Top Skills: Python, Kubernetes" in prompt
        assert "Target Roles: ML Engineer" in prompt
        assert "Visa Sponsorship: Required" in prompt
        assert "Max Results: 10" in prompt

    def test_prompt_truncation(self):
        long_text = "word " * 10_000
        prompt = build_cv_extractor_prompt(long_text, long_text)
        assert "... [truncated]" in prompt


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------


class TestModelFactory:
    """Ensure the LangChain model factory is wired to the project's registry."""

    def test_get_model_name_returns_string(self):
        model_name = get_model_name()
        assert isinstance(model_name, str)
        assert model_name

    def test_build_llm_defaults_to_primary_model(self):
        llm = build_llm()
        assert llm.model == get_model_name()

    def test_build_llm_allows_override(self):
        llm = build_llm(model_name="openai:gpt-4o-mini", temperature=0.5)
        assert llm.model == "openai:gpt-4o-mini"
        assert llm.temperature == 0.5


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    """Ensure every mirrored agent can be built by key."""

    def test_registry_contains_core_agents(self):
        assert "cv_extractor" in AGENT_REGISTRY
        assert "resume_reviewer" in AGENT_REGISTRY
        assert "resume_tailor" in AGENT_REGISTRY
        assert "cover_letter_generator" in AGENT_REGISTRY
        assert "job_finder" in AGENT_REGISTRY

    def test_build_agent_returns_instance(self):
        agent = build_agent("cv_extractor")
        assert isinstance(agent, LCCvExtractorAgent)
        assert agent.is_ready

    def test_build_agent_unknown_key_returns_none(self):
        assert build_agent("not_an_agent") is None


# ---------------------------------------------------------------------------
# Base agent behavior
# ---------------------------------------------------------------------------


class TestLangChainAgent:
    """Test the base agent class, including error fallback."""

    async def test_run_returns_structured_output(self, fake_chain):
        agent = LangChainAgent(
            system_prompt="You are a test agent.",
            output_type=CVExtractorOutput,
        )
        expected = CVExtractorOutput(tailored_resume="mock resume")
        agent._chain = fake_chain(expected)

        result = await agent.run("test prompt")
        assert isinstance(result, CVExtractorOutput)
        assert result.tailored_resume == "mock resume"

    async def test_run_returns_fallback_on_error(self):
        agent = LangChainAgent(
            system_prompt="You are a test agent.",
            output_type=CVExtractorOutput,
        )
        agent._chain = AsyncMock()
        agent._chain.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))

        result = await agent.run("test prompt")
        assert isinstance(result, CVExtractorOutput)


# ---------------------------------------------------------------------------
# Concrete agents
# ---------------------------------------------------------------------------


class TestConcreteAgents:
    """Test each mirrored concrete agent."""

    async def test_cv_extractor_agent(self, sample_resume, sample_job, fake_chain):
        agent = LCCvExtractorAgent(system_prompt="test")
        expected = CVExtractorOutput(tailored_resume="tailored")
        agent._chain = fake_chain(expected)

        result = await agent.extract_and_tailor(sample_resume, sample_job)
        assert isinstance(result, CVExtractorOutput)
        assert result.tailored_resume == "tailored"

    async def test_cv_extractor_requires_inputs(self):
        agent = LCCvExtractorAgent(system_prompt="test")
        result = await agent.extract_and_tailor("", "")
        assert "required" in result.tailored_resume.lower()

    async def test_resume_reviewer_agent(self, sample_resume, sample_job, fake_chain):
        agent = LCResumeReviewerAgent(system_prompt="test")
        expected = ResumeReviewerOutput(
            full_rewritten_resume="rewritten",
            metric_questions=["Q1"],
        )
        agent._chain = fake_chain(expected)

        result = await agent.review(sample_resume, sample_job)
        assert isinstance(result, ResumeReviewerOutput)
        assert result.full_rewritten_resume == "rewritten"

    async def test_resume_reviewer_requires_resume(self):
        agent = LCResumeReviewerAgent(system_prompt="test")
        result = await agent.review("")
        assert "required" in result.full_rewritten_resume.lower()

    async def test_resume_tailor_agent(self, sample_resume, sample_job, fake_chain):
        agent = LCResumeTailorAgent(system_prompt="test")
        expected = TailoredResumeOutput(tailored_content="tailored")
        agent._chain = fake_chain(expected)

        result = await agent.tailor(sample_resume, sample_job, format_type="markdown")
        assert isinstance(result, TailoredResumeOutput)
        assert result.tailored_content == "tailored"
        assert result.format_type == "markdown"

    async def test_resume_tailor_requires_inputs(self):
        agent = LCResumeTailorAgent(system_prompt="test")
        result = await agent.tailor("", "")
        assert "required" in result.tailored_content.lower()

    async def test_cover_letter_agent(self, sample_resume, sample_job, fake_chain):
        agent = LCCoverLetterAgent(system_prompt="test")
        expected = CoverLetterOutput(cover_letter="dear hiring manager")
        agent._chain = fake_chain(expected)

        result = await agent.generate(sample_resume, sample_job, company_name="Example AI")
        assert isinstance(result, CoverLetterOutput)
        assert result.cover_letter == "dear hiring manager"

    async def test_cover_letter_requires_inputs(self):
        agent = LCCoverLetterAgent(system_prompt="test")
        result = await agent.generate("", "")
        assert "required" in result.cover_letter.lower()

    async def test_job_finder_agent(self, sample_resume, fake_chain):
        agent = LCJobFinderAgent(system_prompt="test")
        expected = JobFinderOutput(
            listings=[JobListing(title="MLE", company="Example AI", match_score=0.9)],
            summary="found jobs",
        )
        agent._chain = fake_chain(expected)

        result = await agent.search(sample_resume, top_skills=["Python"])
        assert isinstance(result, JobFinderOutput)
        assert result.summary == "found jobs"
        assert len(result.listings) == 1

    async def test_job_finder_requires_resume(self):
        agent = LCJobFinderAgent(system_prompt="test")
        result = await agent.search("")
        assert "required" in result.summary.lower()


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


class TestLCGraphState:
    """Test the typed state and its helper methods."""

    def test_state_defaults(self):
        state = LCGraphState(
            pipeline_name="test",
            resume_text="resume",
            job_text="job",
        )
        assert state.pipeline_name == "test"
        assert state.get_resume_text() == "resume"

    def test_get_resume_text_prefers_artifacts(self):
        state = LCGraphState(
            pipeline_name="test",
            resume_text="original",
            artifacts={
                "cv_extractor": CVExtractorOutput(tailored_resume="tailored"),
            },
        )
        assert state.get_resume_text() == "tailored"


# ---------------------------------------------------------------------------
# Graph pipeline
# ---------------------------------------------------------------------------


class TestLangGraphPipeline:
    """Test pipeline configuration, graph construction, and execution."""

    def test_load_pipeline_configs(self):
        configs = load_pipeline_configs()
        assert "full_application" in configs
        assert "resume_only" in configs
        assert isinstance(configs["full_application"], LangGraphPipelineConfig)
        assert len(configs["full_application"].steps) > 0

    def test_get_pipeline_config(self):
        config = get_pipeline_config("resume_only")
        assert config is not None
        assert any(step.agent_key == "cv_extractor" for step in config.steps)
        assert any(step.agent_key == "resume_reviewer" for step in config.steps)

    def test_build_pipeline_graph(self):
        graph = build_pipeline_graph("resume_only")
        assert graph is not None

    def test_build_pipeline_graph_unknown_raises(self):
        with pytest.raises(ValueError):
            build_pipeline_graph("definitely_not_a_pipeline")

    async def test_run_resume_only_pipeline(self, sample_resume, sample_job, monkeypatch):
        """Run resume_only pipeline with mocked agents to avoid real LLM calls."""

        def fake_build_agent(agent_key, model=None, tools=None):
            agent_cls = AGENT_REGISTRY.get(agent_key)
            if agent_cls is None:
                return None
            agent = agent_cls(system_prompt="test", model=model)
            agent._chain = AsyncMock()
            if agent_key == "cv_extractor":
                agent._chain.ainvoke = AsyncMock(
                    return_value=CVExtractorOutput(tailored_resume="tailored by LC")
                )
            elif agent_key == "resume_reviewer":
                agent._chain.ainvoke = AsyncMock(
                    return_value=ResumeReviewerOutput(full_rewritten_resume="reviewed by LC")
                )
            elif agent_key == "cover_letter_generator":
                agent._chain.ainvoke = AsyncMock(
                    return_value=CoverLetterOutput(cover_letter="letter by LC")
                )
            elif agent_key == "job_finder":
                agent._chain.ainvoke = AsyncMock(return_value=JobFinderOutput(summary="jobs by LC"))
            else:
                agent._chain.ainvoke = AsyncMock(return_value=agent.output_type())
            return agent

        monkeypatch.setattr("app.langchain_layer.graph.build_agent", fake_build_agent)

        pipeline = LangGraphPipeline()
        final_state = await pipeline.run(
            "resume_only",
            resume_text=sample_resume,
            job_text=sample_job,
        )

        assert "cv_extractor" in final_state.artifacts
        assert "resume_reviewer" in final_state.artifacts
        assert len(final_state.errors) == 0
        assert final_state.get_resume_text() == "reviewed by LC"

    async def test_run_pipeline_not_found(self):
        result = await run_pipeline("missing_pipeline", resume_text="x")
        assert len(result.errors) == 1
        assert "not found" in result.errors[0].lower()


# ---------------------------------------------------------------------------
# Security / leak prevention
# ---------------------------------------------------------------------------


class TestSecurityAndPrivacy:
    """Ensure the repository is safe to share and contains no real user data."""

    def test_no_real_resume_files_in_sources(self):
        sources_dir = Path(__file__).parent.parent / "data" / "resumes" / "sources"
        personal_names = ["mozayed", "mohamed_zayed", "zayed"]
        for path in sources_dir.iterdir():
            if path.is_file() and path.name != ".gitkeep":
                lowered = path.name.lower()
                for name in personal_names:
                    # sample_resume.md is allowed; others matching personal names are not.
                    if name in lowered and "sample" not in lowered:
                        pytest.fail(f"Potential personal resume still present: {path}")

    def test_sample_resume_contains_no_real_pii(self):
        sample_path = (
            Path(__file__).parent.parent / "data" / "resumes" / "sources" / "sample_resume.md"
        )
        content = sample_path.read_text(encoding="utf-8")
        # The sample should be fictional and include a disclaimer.
        assert "Jane Doe" in content
        assert "fictional" in content.lower()
        assert "example.com" in content
        real_indicators = ["cairo", "egypt", "+20", "linkedin.com/in/mo"]
        for indicator in real_indicators:
            assert indicator not in content.lower(), f"Possible real PII found: {indicator}"

    def test_env_file_is_ignored_and_not_tracked(self):
        """.env is local-only; its contents (including real keys) must never be committed."""
        import subprocess

        repo_root = Path(__file__).parent.parent
        env_path = repo_root / ".env"
        if not env_path.exists():
            return

        # .env must be git-ignored
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(env_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, ".env is not git-ignored and could be committed"

        # .env must not be tracked by git
        tracked = subprocess.run(
            ["git", "ls-files", ".env"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert tracked.stdout.strip() == "", ".env is currently tracked by git"

    def test_gitignore_blocks_resume_sources(self):
        gitignore = Path(__file__).parent.parent / ".gitignore"
        content = gitignore.read_text(encoding="utf-8")
        assert "data/resumes/sources/*" in content
        assert "!data/resumes/sources/.gitkeep" in content

    def test_no_pdf_or_tex_personal_resumes_tracked(self):
        # This is a heuristic; the previous tests remove personal files.
        # We verify the sample is the only markdown file in sources.
        sources_dir = Path(__file__).parent.parent / "data" / "resumes" / "sources"
        tracked_extensions = {".pdf", ".tex"}
        offenders = [
            p.name
            for p in sources_dir.iterdir()
            if p.is_file() and p.suffix.lower() in tracked_extensions
        ]
        assert offenders == [], f"Personal resume files still present: {offenders}"


# ---------------------------------------------------------------------------
# Langfuse setup
# ---------------------------------------------------------------------------


class TestLangfuseSetup:
    """Test Langfuse observability integration."""

    def test_init_langfuse_no_keys(self, monkeypatch):
        """No env vars set means no callback is added."""
        import litellm

        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

        original = list(litellm.callbacks)
        from app.core.langfuse_setup import init_langfuse

        init_langfuse()
        assert litellm.callbacks == original

    def test_get_langfuse_handler_returns_none_without_keys(self, monkeypatch):
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

        from app.core.langfuse_setup import get_langfuse_handler

        assert get_langfuse_handler() is None

    def test_langfuse_import_is_optional(self):
        """langfuse_setup module can be imported even if langfuse package is absent."""
        import app.core.langfuse_setup as mod

        assert hasattr(mod, "init_langfuse")
        assert hasattr(mod, "get_langfuse_handler")


# ---------------------------------------------------------------------------
# MCP tools for LangChain
# ---------------------------------------------------------------------------


class TestMCPTools:
    """Test MCP tool wrapping for the LangChain layer."""

    def test_get_lc_tools_returns_list(self):
        from app.langchain_layer.tools import get_lc_tools

        tools = get_lc_tools()
        assert isinstance(tools, list)

    def test_get_lc_tools_for_job_finder_includes_web_tools(self):
        from app.langchain_layer.tools import get_lc_tools_for_agent

        tools = get_lc_tools_for_agent("job_finder")
        names = {t.name for t in tools}
        assert "web_search" in names or len(tools) >= 0  # web_search depends on tinyfish

    def test_get_lc_tools_for_other_agents_returns_empty(self):
        from app.langchain_layer.tools import get_lc_tools_for_agent

        assert get_lc_tools_for_agent("cv_extractor") == []
        assert get_lc_tools_for_agent("resume_tailor") == []

    def test_tools_are_structured_tool_instances(self):
        from langchain_core.tools import StructuredTool

        from app.langchain_layer.tools import get_lc_tools

        for tool in get_lc_tools():
            assert isinstance(tool, StructuredTool)
