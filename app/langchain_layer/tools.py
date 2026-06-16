"""MCP tools adapted for the LangChain layer.

Wraps the existing ``app.ax.tool_registry`` handlers as LangChain
``StructuredTool`` objects so both AI layers share the same tool definitions
and handler implementations.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from loguru import logger

from app.ax.tool_registry import get_tool_definitions, resolve_handler


def get_lc_tools() -> list[StructuredTool]:
    """Return all available LangChain tools for the current environment.

    Each tool is a ``StructuredTool`` wrapping an existing handler from
    ``app.ax.tool_registry``. Tools without a resolvable handler are skipped.
    """
    tools: list[StructuredTool] = []
    definitions = get_tool_definitions()

    for name, spec in definitions.items():
        handler = resolve_handler(name)
        if handler is None:
            continue

        try:
            tool = StructuredTool.from_function(
                coroutine=handler,
                name=name,
                description=spec.get("description", ""),
            )
            tools.append(tool)
        except Exception as exc:
            logger.debug(f"Failed to create StructuredTool for '{name}': {exc}")

    return tools


# Map agent keys to the tool names they should receive.
# Mirrors the `tools` class attribute on Pydantic AI agents.
_AGENT_TOOL_MAP: dict[str, list[str]] = {
    "job_finder": ["web_search", "web_fetch", "search_imported_jobs", "list_imported_startups"],
}


def get_lc_tools_for_agent(agent_key: str) -> list[StructuredTool]:
    """Return tools for a specific LangChain agent, matching the Pydantic AI layer."""
    tool_names = _AGENT_TOOL_MAP.get(agent_key, [])
    if not tool_names:
        return []

    all_tools = get_lc_tools()
    return [t for t in all_tools if t.name in tool_names]
