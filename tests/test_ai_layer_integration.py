"""Integration tests for the AI layer: Langfuse, Pydantic AI, LangChain,
pydantic-graph, and the AX/MCP tool surface.

These verify the layers are wired together correctly (trace attribution,
handler wiring, tool availability) without making real LLM calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Pydantic AI agent attribution (Langfuse / Logfire trace naming)
# ---------------------------------------------------------------------------


class TestAgentAttribution:
    """create_agent must forward name/description to pydantic-ai Agent."""

    def test_create_agent_forwards_name(self):
        from app.core.model_registry import create_agent

        agent = create_agent(system_prompt="test", name="Job Finder")
        assert agent.name == "Job Finder"

    def test_create_agent_omits_name_when_none(self):
        from app.core.model_registry import create_agent

        agent = create_agent(system_prompt="test")
        assert agent.name is None or agent.name == ""

    def test_base_agent_passes_config_name(self):
        """BaseAgent built from agents.yaml carries its config name onto the Agent."""
        from pathlib import Path

        from app.agents.base_agent import AgentConfig, BaseAgent

        class DummyAgent(BaseAgent):
            output_type = None

            async def execute(self, state):
                pass

        config = AgentConfig(name="CV Extractor")
        agent = DummyAgent(config, Path("."))
        assert agent._agent is not None
        assert agent._agent.name == "CV Extractor"


# ---------------------------------------------------------------------------
# Langfuse setup
# ---------------------------------------------------------------------------


class TestLangfuseIntegration:
    """Langfuse helpers must be safe without credentials and explicit with them."""

    def test_is_langfuse_enabled_false_without_keys(self, monkeypatch):
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        from app.core.langfuse_setup import is_langfuse_enabled

        assert is_langfuse_enabled() is False

    def test_is_langfuse_enabled_true_with_explicit_keys(self):
        from app.core.langfuse_setup import is_langfuse_enabled

        assert is_langfuse_enabled(public_key="pk-test", secret_key="sk-test") is True

    def test_get_langfuse_handler_none_without_keys(self, monkeypatch):
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        from app.core.langfuse_setup import get_langfuse_handler

        assert get_langfuse_handler() is None

    def test_get_langfuse_handler_with_explicit_keys(self):
        from app.core.langfuse_setup import get_langfuse_handler

        handler = get_langfuse_handler(public_key="pk-test", secret_key="sk-test")
        assert handler is not None

    def test_build_langgraph_config_none_without_keys(self, monkeypatch):
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        from app.core.langfuse_setup import build_langgraph_config

        assert build_langgraph_config("resume_only") is None

    def test_build_langgraph_config_carries_metadata(self):
        from app.core.langfuse_setup import build_langgraph_config

        cfg = build_langgraph_config("full_application", public_key="pk-test", secret_key="sk-test")
        assert cfg is not None
        assert "callbacks" in cfg
        assert len(cfg["callbacks"]) == 1
        assert cfg["metadata"]["langfuse_session_id"] == "full_application"
        assert cfg["metadata"]["pipeline"] == "full_application"

    def test_init_langfuse_no_keys_is_noop(self, monkeypatch):
        import litellm

        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        before = list(litellm.callbacks)
        from app.core.langfuse_setup import init_langfuse

        init_langfuse()
        assert litellm.callbacks == before


# ---------------------------------------------------------------------------
# LangChain graph uses the Langfuse config helper
# ---------------------------------------------------------------------------


class TestLangGraphLangfuseWiring:
    """graph.py should use build_langgraph_config (not a raw handler)."""

    async def test_pipeline_uses_langgraph_config_helper(self, monkeypatch):
        """When Langfuse is enabled, graph.ainvoke receives a config with metadata."""
        from app.agents.cv_extractor import CVExtractorOutput
        from app.agents.resume_reviewer import ResumeReviewerOutput
        from app.langchain_layer.agents import AGENT_REGISTRY
        from app.langchain_layer.graph import LangGraphPipeline

        captured: dict = {}

        def fake_build_agent(agent_key, model=None, tools=None):
            cls = AGENT_REGISTRY[agent_key]
            agent = cls(system_prompt="test", model=model)
            agent._chain = AsyncMock()
            agent._chain.ainvoke = AsyncMock(
                return_value=CVExtractorOutput(tailored_resume="t")
                if agent_key == "cv_extractor"
                else ResumeReviewerOutput(full_rewritten_resume="r")
            )
            return agent

        async def fake_ainvoke(state, config=None):
            captured["config"] = config
            # Simulate the two resume_only steps
            state.artifacts["cv_extractor"] = CVExtractorOutput(tailored_resume="t")
            state.artifacts["resume_reviewer"] = ResumeReviewerOutput(full_rewritten_resume="r")
            return state

        monkeypatch.setattr("app.langchain_layer.graph.build_agent", fake_build_agent)
        monkeypatch.setattr(
            "app.core.langfuse_setup.build_langgraph_config",
            lambda name: {"callbacks": [], "metadata": {"pipeline": name}},
        )

        compiled = AsyncMock()
        compiled.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.langchain_layer.graph.build_pipeline_graph",
            lambda key: compiled,
        )

        pipeline = LangGraphPipeline()
        await pipeline.run("resume_only", resume_text="x", job_text="y")

        assert captured["config"] is not None
        assert captured["config"]["metadata"]["pipeline"] == "Resume Tailoring Only"

    async def test_pipeline_works_without_langfuse(self, monkeypatch):
        """When Langfuse is disabled (None config), ainvoke still runs with config=None."""
        from app.agents.cv_extractor import CVExtractorOutput
        from app.agents.resume_reviewer import ResumeReviewerOutput
        from app.langchain_layer.agents import AGENT_REGISTRY
        from app.langchain_layer.graph import LangGraphPipeline

        captured: dict = {}

        def fake_build_agent(agent_key, model=None, tools=None):
            cls = AGENT_REGISTRY[agent_key]
            agent = cls(system_prompt="test", model=model)
            agent._chain = AsyncMock()
            agent._chain.ainvoke = AsyncMock(
                return_value=CVExtractorOutput(tailored_resume="t")
                if agent_key == "cv_extractor"
                else ResumeReviewerOutput(full_rewritten_resume="r")
            )
            return agent

        async def fake_ainvoke(state, config=None):
            captured["config"] = config
            state.artifacts["cv_extractor"] = CVExtractorOutput(tailored_resume="t")
            state.artifacts["resume_reviewer"] = ResumeReviewerOutput(full_rewritten_resume="r")
            return state

        monkeypatch.setattr("app.langchain_layer.graph.build_agent", fake_build_agent)
        monkeypatch.setattr("app.core.langfuse_setup.build_langgraph_config", lambda name: None)
        compiled = AsyncMock()
        compiled.ainvoke = fake_ainvoke
        monkeypatch.setattr(
            "app.langchain_layer.graph.build_pipeline_graph",
            lambda key: compiled,
        )

        pipeline = LangGraphPipeline()
        result = await pipeline.run("resume_only", resume_text="x", job_text="y")
        assert captured["config"] is None
        assert "cv_extractor" in result.artifacts


# ---------------------------------------------------------------------------
# Pydantic-graph engine tracing (logfire span wrapper)
# ---------------------------------------------------------------------------


class TestPydanticGraphTracing:
    """graph_engine wraps pipeline runs in a logfire span (no-op when absent)."""

    def test_span_helper_returns_context_when_logfire_none(self, monkeypatch):
        import app.pipelines.graph_engine as ge

        monkeypatch.setattr(ge, "logfire", None)
        ctx = ge._span("test")
        with ctx:
            pass

    def test_span_helper_uses_logfire_when_present(self, monkeypatch):
        import app.pipelines.graph_engine as ge

        calls: list[str] = []

        class FakeSpan:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        class FakeLogfire:
            def span(self, name, **kwargs):
                calls.append(name)
                return FakeSpan()

        monkeypatch.setattr(ge, "logfire", FakeLogfire())
        with ge._span("pydantic_graph:resume_only", pipeline="x"):
            pass
        assert calls == ["pydantic_graph:resume_only"]


# ---------------------------------------------------------------------------
# AX / MCP tool availability
# ---------------------------------------------------------------------------


class TestAXToolAvailability:
    """Tool registry distinguishes callable tools from descriptor-only inbound MCPs."""

    def test_get_available_tools_excludes_inbound_only(self):
        from app.ax.tool_registry import get_available_tools, get_tool_definitions

        all_tools = get_tool_definitions()
        available = get_available_tools()
        assert "web_search" in available
        assert "search_imported_jobs" in available
        assert len(available) <= len(all_tools)

    def test_manifest_marks_availability(self):
        from app.ax.tool_registry import get_manifest_tools, resolve_handler

        manifest = get_manifest_tools()
        assert manifest, "expected at least one tool in manifest"
        for entry in manifest:
            assert "available" in entry
            assert entry["available"] == (resolve_handler(entry["name"]) is not None)
            assert "inbound" in entry
            assert "source" in entry

    def test_manifest_includes_inbound_descriptors_as_unavailable(self):
        """External MCP descriptors (github/notion/supabase) appear but are not callable."""
        from app.ax.tool_registry import get_manifest_tools, resolve_handler

        manifest = get_manifest_tools()
        names = {t["name"]: t for t in manifest}
        # search_code is a github MCP descriptor with no local handler
        if "search_code" in names:
            assert names["search_code"]["available"] is False
            assert names["search_code"]["inbound"] is True
            assert resolve_handler("search_code") is None

    def test_ax_package_exports(self):
        from app.ax import (
            get_available_tools,
            get_manifest_tools,
            get_tool_definitions,
            resolve_handler,
        )

        assert callable(get_available_tools)
        assert callable(get_manifest_tools)
        assert callable(get_tool_definitions)
        assert callable(resolve_handler)


# ---------------------------------------------------------------------------
# AX API surface
# ---------------------------------------------------------------------------


class TestAXRoutes:
    """The /api/ax endpoints surface tools and agents to clients."""

    def test_ax_tools_endpoint(self):
        client = TestClient(app)
        resp = client.get("/api/ax/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["count"] == len(data["tools"])
        assert data["available_count"] <= data["count"]
        assert all("available" in t for t in data["tools"])

    def test_ax_available_tools_endpoint(self):
        client = TestClient(app)
        resp = client.get("/api/ax/tools/available")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["count"] == len(data["tools"])
        assert all("inputSchema" in t for t in data["tools"])

    def test_ax_agents_endpoint(self):
        client = TestClient(app)
        resp = client.get("/api/ax/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert isinstance(data["agents"], list)


# ---------------------------------------------------------------------------
# Pydantic AI MCP toolset surface (agents accept toolsets)
# ---------------------------------------------------------------------------


class TestPydanticAIMcpToolsetSurface:
    """Sanity-check that pydantic-ai Agent accepts a toolsets kwarg (MCP entry point)."""

    def test_agent_accepts_toolsets_kwarg(self):
        from app.core.model_registry import create_agent

        agent = create_agent(system_prompt="t", name="t", toolsets=[])
        assert agent is not None
