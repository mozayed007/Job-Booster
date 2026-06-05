"""Merge outbound MCP tools with inbound mcps/ descriptors."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Awaitable, Callable

from loguru import logger

from app.core.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_TOOLS = PROJECT_ROOT / "profiles" / "tools" / "mcp_tools.json"


def _load_json_tools(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load tools from {}: {}", path, e)
        return {}
    tools: dict[str, dict[str, Any]] = {}
    for entry in data.get("tools", []):
        name = entry.get("name")
        if name:
            tools[name] = entry
    return tools


def _load_inbound_mcps(mcps_dir: Path) -> dict[str, dict[str, Any]]:
    inbound: dict[str, dict[str, Any]] = {}
    if not mcps_dir.is_dir():
        return inbound
    for path in sorted(mcps_dir.glob("**/tools/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        entries = data.get("tools", [data]) if isinstance(data, dict) else []
        if isinstance(data, dict) and "name" in data and "inputSchema" in data:
            entries = [data]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not name or name in inbound:
                continue
            inbound[name] = {
                "name": name,
                "description": entry.get("description", ""),
                "inputSchema": entry.get("inputSchema", {"type": "object", "properties": {}}),
                "_inbound": True,
                "_source": str(path.relative_to(PROJECT_ROOT)),
            }
    return inbound


@lru_cache(maxsize=1)
def get_tool_definitions() -> dict[str, dict[str, Any]]:
    """Canonical + merged inbound tool descriptors."""
    outbound = _load_json_tools(DEFAULT_MCP_TOOLS)
    merged = dict(outbound)

    if getattr(settings, "AX_MERGE_INBOUND_MCPS", True):
        mcps_dir = PROJECT_ROOT / getattr(settings, "AX_MCPS_DIR", "mcps")
        inbound = _load_inbound_mcps(mcps_dir)
        skipped = 0
        for name, spec in inbound.items():
            if name in merged:
                skipped += 1
                continue
            merged[name] = spec
        if skipped:
            logger.debug("AX registry skipped {} inbound name collisions", skipped)

    return merged


def get_manifest_tools() -> list[dict[str, Any]]:
    """MCP tools/list payload (without internal keys)."""
    tools = []
    for spec in get_tool_definitions().values():
        tools.append({
            "name": spec["name"],
            "description": spec.get("description", ""),
            "inputSchema": spec.get("inputSchema", {}),
        })
    return tools


def resolve_handler(tool_name: str) -> Callable[..., Awaitable[str]] | None:
    """Return async handler for a tool name, if implemented in Job Booster."""
    from app.agents import discovery_tools
    from app.agents.web_tools import web_fetch, web_search

    handlers: dict[str, Callable[..., Awaitable[str]]] = {
        "web_search": web_search,
        "web_fetch": web_fetch,
        "search_imported_jobs": discovery_tools.search_imported_jobs_tool,
        "list_imported_startups": discovery_tools.list_imported_startups_tool,
        "list_bigset_mappings": discovery_tools.list_bigset_mappings_tool,
        "sync_bigset_folder": discovery_tools.sync_bigset_folder_tool,
        "imported_jobs_for_company": discovery_tools.imported_jobs_for_company_tool,
    }
    return handlers.get(tool_name)