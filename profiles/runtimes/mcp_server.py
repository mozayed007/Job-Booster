"""MCP Agent Server — serves all agent profiles as callable MCP tools.

This turns each agent profile into an MCP tool that any MCP-compatible
host (Cursor, Claude Code, opencode, etc.) can call. The server:

1. Loads all agent profiles from profiles/agents/
2. Resolves LLM providers from profiles/providers.yaml
3. Creates an MCP tool per agent with the profile's I/O contract
4. Routes calls to the appropriate LLM with fallback chains

Usage:
    # Run as stdio MCP server (for Cursor, Claude Code)
    python profiles/runtimes/mcp_server.py

    # Run as SSE MCP server (for web clients)
    python profiles/runtimes/mcp_server.py --transport sse --port 8051
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import yaml

# Add parent dirs to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

PROFILES_DIR = Path(__file__).parent.parent
AGENTS_DIR = PROFILES_DIR / "agents"
TOOLS_FILE = PROFILES_DIR / "tools" / "mcp_tools.json"


def load_mcp_tools() -> dict[str, Any]:
    """Load MCP tool definitions (outbound + optional inbound mcps/)."""
    try:
        from app.ax.tool_registry import get_tool_definitions

        return get_tool_definitions()
    except Exception:
        with open(TOOLS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return {t["name"]: t for t in data.get("tools", [])}


def load_agent_profiles() -> dict[str, dict[str, Any]]:
    """Load all agent profiles."""
    agents = {}
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        key = profile["meta"]["name"]
        agents[key] = profile
    return agents


def profile_to_mcp_tool(name: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Convert an agent profile to an MCP tool definition."""
    meta = profile["meta"]
    io_def = profile.get("io", {})
    inputs = io_def.get("inputs", [])

    # Build JSON Schema for inputs
    properties = {}
    required = []
    for inp in inputs:
        prop: dict[str, Any] = {
            "type": inp["type"],
            "description": inp["description"],
        }
        if "default" in inp:
            prop["default"] = inp["default"]
        properties[inp["name"]] = prop
        if inp.get("required"):
            required.append(inp["name"])

    input_schema = {
        "type": "object",
        "properties": properties,
    }
    if required:
        input_schema["required"] = required

    return {
        "name": f"agent_{name}",
        "description": f"{meta['display_name']}: {meta['description']}",
        "inputSchema": input_schema,
        "annotations": {
            "profile_name": name,
            "version": meta.get("version", "1.0.0"),
            "tags": meta.get("tags", []),
        },
    }


def build_mcp_manifest() -> dict[str, Any]:
    """Build the full MCP server manifest with all agents as tools."""
    profiles = load_agent_profiles()
    mcp_tools = load_mcp_tools()

    tools = []

    # Add utility tools (web_search, web_fetch, etc.)
    for tool_name, tool_def in mcp_tools.items():
        tools.append(
            {
                "name": tool_name,
                "description": tool_def["description"],
                "inputSchema": tool_def["inputSchema"],
            }
        )

    # Add agent tools
    for name, profile in profiles.items():
        tools.append(profile_to_mcp_tool(name, profile))

    return {
        "name": "job-booster-agents",
        "version": "1.0.0",
        "description": "Portable agent profiles served as MCP tools",
        "tools": tools,
    }


# ──────────────────────────────────────────────
# MCP Protocol Implementation (stdio transport)
# ──────────────────────────────────────────────


class MCPServer:
    """Minimal MCP stdio server for agent profiles."""

    def __init__(self) -> None:
        self.manifest = build_mcp_manifest()
        self.tools_map = {t["name"]: t for t in self.manifest["tools"]}

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle a single JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": self.manifest["name"],
                        "version": self.manifest["version"],
                    },
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.manifest["tools"]},
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            return await self._call_tool(tool_name, arguments, req_id)

        elif method == "notifications/initialized":
            # Notification, no response needed
            return {}

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

    async def _call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        req_id: Any,
    ) -> dict[str, Any]:
        """Handle a tool call."""
        if tool_name not in self.tools_map:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32602,
                    "message": f"Unknown tool: {tool_name}",
                },
            }

        # For agent tools, build the prompt and call the LLM
        if tool_name.startswith("agent_"):
            return await self._run_agent(tool_name, arguments, req_id)

        try:
            from app.ax.tool_registry import resolve_handler
            import inspect

            handler = resolve_handler(tool_name)
            if handler is not None:
                try:
                    text = await handler(**arguments)
                except TypeError:
                    sig = inspect.signature(handler)
                    filtered = {
                        k: v for k, v in arguments.items() if k in sig.parameters
                    }
                    text = await handler(**filtered)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": str(text)}],
                    },
                }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(e)},
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32602,
                "message": f"Tool '{tool_name}' has no runtime handler in Job Booster",
            },
        }

    async def _run_agent(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        req_id: Any,
    ) -> dict[str, Any]:
        """Run an agent by building a prompt and calling the LLM."""
        profile_name = tool_name.removeprefix("agent_")
        profiles = load_agent_profiles()
        profile = profiles.get(profile_name)

        if not profile:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32602,
                    "message": f"Profile not found: {profile_name}",
                },
            }

        # Build the user message from inputs
        io_def = profile.get("io", {})
        input_defs = io_def.get("inputs", [])
        user_parts = []
        for inp in input_defs:
            name = inp["name"]
            if name in arguments:
                user_parts.append(f"## {name}\n{arguments[name]}")

        user_message = "\n\n".join(user_parts)
        system_prompt = profile.get("instructions", "")

        # Resolve LLM provider
        try:
            from profiles.provider_resolver import resolve_chain

            primary, fallbacks = resolve_chain()
        except Exception:
            primary, fallbacks = "", []

        if not primary:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "No LLM provider available. "
                                "Set an API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.) "
                                "or start a local model (Ollama, vLLM)."
                            ),
                        }
                    ],
                    "isError": True,
                },
            }

        # Call the LLM (generic OpenAI-compatible)
        try:
            from profiles.runtimes.generic_runner import call_llm

            result = await call_llm(
                system_prompt=system_prompt,
                user_message=user_message,
                model_string=primary,
                fallbacks=fallbacks,
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result}],
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Agent execution failed: {e}"}],
                    "isError": True,
                },
            }

    async def run_stdio(self) -> None:
        """Run the server on stdio transport."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        buffer = ""
        while True:
            data = await reader.read(4096)
            if not data:
                break
            buffer += data.decode("utf-8")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)
                    if response:
                        sys.stdout.write(json.dumps(response) + "\n")
                        sys.stdout.flush()
                except json.JSONDecodeError:
                    pass

    async def run_sse(self, host: str = "0.0.0.0", port: int = 8051) -> None:
        """Run the server on SSE transport."""
        try:
            from aiohttp import web
        except ImportError:
            print("aiohttp required for SSE transport: pip install aiohttp")
            sys.exit(1)

        async def handle_sse(request: web.Request) -> web.StreamResponse:
            response = web.StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
            await response.prepare(request)

            # Send manifest
            manifest_data = json.dumps(self.manifest)
            await response.write(f"data: {manifest_data}\n\n".encode())

            return response

        async def handle_message(request: web.Request) -> web.Response:
            body = await request.json()
            response = await self.handle_request(body)
            return web.json_response(response)

        app = web.Application()
        app.router.add_get("/sse", handle_sse)
        app.router.add_post("/message", handle_message)

        print(f"MCP SSE server running on http://{host}:{port}")
        web.run_app(app, host=host, port=port)


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="MCP Agent Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument("--port", type=int, default=8051, help="Port for SSE transport")
    args = parser.parse_args()

    server = MCPServer()

    if args.transport == "stdio":
        await server.run_stdio()
    else:
        await server.run_sse(port=args.port)


if __name__ == "__main__":
    asyncio.run(main())
