"""Tests for AX tool registry."""

from app.ax.tool_registry import get_tool_definitions, resolve_handler


class TestAxToolRegistry:
    def test_loads_outbound_tools(self):
        tools = get_tool_definitions()
        assert "web_search" in tools
        assert "search_imported_jobs" in tools

    def test_resolve_discovery_handlers(self):
        assert resolve_handler("search_imported_jobs") is not None
        assert resolve_handler("sync_bigset_folder") is not None
        assert resolve_handler("web_search") is not None

    def test_inbound_merge_adds_descriptors(self):
        tools = get_tool_definitions()
        assert len(tools) > 10