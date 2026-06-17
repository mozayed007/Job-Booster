"""Agent experience (AX) — surface MCP tools and agent profiles to clients.

Exposes the merged tool manifest (with availability flags) and the list of
agent profiles so UIs and external MCP clients can discover what the agentic
layer can actually do.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.profile_loader import list_available_agents
from app.ax.tool_registry import get_available_tools, get_manifest_tools

router = APIRouter(prefix="/ax", tags=["AgentExperience"])


@router.get("/tools")
async def ax_tools():
    """List all known MCP tools with availability + source.

    ``available=True`` means Job Booster has a handler and the tool can be
    invoked from this process (Pydantic AI / LangChain agents). Inbound-only
    descriptors cached from external MCP servers are returned with
    ``available=False``.
    """
    manifest = get_manifest_tools()
    return {
        "success": True,
        "count": len(manifest),
        "available_count": sum(1 for t in manifest if t["available"]),
        "tools": manifest,
    }


@router.get("/tools/available")
async def ax_available_tools():
    """List only tools that agents can actually call (have a resolvable handler)."""
    tools = [
        {
            "name": name,
            "description": spec.get("description", ""),
            "inputSchema": spec.get("inputSchema", {}),
        }
        for name, spec in get_available_tools().items()
    ]
    return {"success": True, "count": len(tools), "tools": tools}


@router.get("/agents")
async def ax_agents():
    """List agent profiles from ``profiles/agents/*.yaml``."""
    agents = list_available_agents()
    return {"success": True, "count": len(agents), "agents": agents}
