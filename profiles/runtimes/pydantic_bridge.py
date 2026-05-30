"""Pydantic AI Bridge — connects agent profiles with the existing Pydantic AI runtime.

This adapter reads profiles from profiles/agents/ and creates Pydantic AI
Agent instances, preserving the existing BaseAgent interface while using
profiles as the source of truth.

Usage:
    from profiles.runtimes.pydantic_bridge import create_agent_from_profile

    agent = create_agent_from_profile("job-finder")
    result = await agent.run("Find me ML jobs")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Type

import yaml
from pydantic import BaseModel, create_model
from pydantic_ai import Agent

from profiles.provider_resolver import resolve_chain


PROFILES_DIR = Path(__file__).parent.parent
AGENTS_DIR = PROFILES_DIR / "agents"


def _load_profile(name: str) -> dict[str, Any]:
    """Load an agent profile by name."""
    path = AGENTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_output_model(profile: dict[str, Any]) -> type[BaseModel] | None:
    """Build a Pydantic model from the profile's output schema."""
    io_def = profile.get("io", {})
    outputs = io_def.get("outputs", [])

    if not outputs:
        return None

    fields: dict[str, Any] = {}
    for out in outputs:
        name = out["name"]
        out_type = out.get("type", "string")

        # Map JSON Schema types to Python types
        type_map = {
            "string": (str, ""),
            "number": (float, 0.0),
            "integer": (int, 0),
            "boolean": (bool, False),
            "array": (list, []),
            "object": (dict, {}),
        }

        python_type, default = type_map.get(out_type, (str, ""))
        fields[name] = (python_type, default)

    if not fields:
        return None

    return create_model(
        f"{profile['meta']['name'].replace('-', '_').title()}Output",
        **fields,
    )


def create_agent_from_profile(
    profile_name: str,
    tools: list[Any] | None = None,
    model_string: str | None = None,
) -> Agent:
    """Create a Pydantic AI Agent from a profile.

    Args:
        profile_name: Agent profile name (kebab-case)
        tools: Optional list of Pydantic AI Tool objects
        model_string: Explicit model string (overrides provider resolution)

    Returns:
        Configured Pydantic AI Agent instance
    """
    profile = _load_profile(profile_name)
    instructions = profile.get("instructions", "")

    # Resolve model
    if model_string is None:
        model_string, _ = resolve_chain()
        if not model_string:
            raise Exception(
                "No LLM provider available. "
                "Set an API key or start a local model."
            )

    # Build output type
    output_type = _build_output_model(profile)

    # Create agent
    agent_kwargs: dict[str, Any] = {
        "model": model_string,
        "system_prompt": instructions,
    }

    if output_type:
        agent_kwargs["output_type"] = output_type

    if tools:
        agent_kwargs["tools"] = tools

    return Agent(**agent_kwargs)


def list_profile_agents() -> list[dict[str, Any]]:
    """List all available profile agents with their metadata."""
    agents = []
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        meta = profile.get("meta", {})
        io_def = profile.get("io", {})
        agents.append({
            "name": meta.get("name", ""),
            "display_name": meta.get("display_name", ""),
            "description": meta.get("description", ""),
            "inputs": [
                {"name": i["name"], "type": i["type"], "required": i.get("required", False)}
                for i in io_def.get("inputs", [])
            ],
            "outputs": [
                {"name": o["name"], "type": o["type"]}
                for o in io_def.get("outputs", [])
            ],
        })
    return agents


async def run_profile_agent(
    profile_name: str,
    inputs: dict[str, Any],
    tools: list[Any] | None = None,
    model_string: str | None = None,
) -> dict[str, Any]:
    """Run a profile agent and return structured output.

    Args:
        profile_name: Agent profile name (kebab-case)
        inputs: Input values matching the profile's I/O contract
        tools: Optional Pydantic AI tools
        model_string: Explicit model to use

    Returns:
        Dict with the agent's output fields
    """
    agent = create_agent_from_profile(profile_name, tools, model_string)

    # Build user message from inputs
    profile = _load_profile(profile_name)
    io_def = profile.get("io", {})
    input_defs = io_def.get("inputs", [])
    user_parts = []
    for inp in input_defs:
        name = inp["name"]
        if name in inputs:
            value = inputs[name]
            if isinstance(value, (list, dict)):
                value = json.dumps(value, indent=2)
            user_parts.append(f"## {name}\n{value}")

    user_message = "\n\n".join(user_parts)

    result = await agent.run(user_message)

    if hasattr(result, "output") and isinstance(result.output, BaseModel):
        return result.output.model_dump()
    return {"result": str(result)}
