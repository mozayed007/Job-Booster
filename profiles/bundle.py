"""Bundle all agent profiles into a single portable file.

Usage:
    python profiles/bundle.py                  # Write to profiles/bundle.yaml
    python profiles/bundle.py --output out.yaml
    python profiles/bundle.py --specialize field="software engineering" industry="tech"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


PROFILES_DIR = Path(__file__).parent
AGENTS_DIR = PROFILES_DIR / "agents"
PIPELINES_FILE = PROFILES_DIR / "pipelines.yaml"
SCHEMA_FILE = PROFILES_DIR / "schema.yaml"
TOOLS_DIR = PROFILES_DIR / "tools"
PROVIDERS_FILE = PROFILES_DIR / "providers.yaml"


def load_agent_profiles() -> dict[str, Any]:
    """Load all agent YAML files from agents/ directory."""
    agents = {}
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        key = profile["meta"]["name"]
        agents[key] = profile
    return agents


def load_pipelines() -> dict[str, Any]:
    """Load pipeline definitions."""
    with open(PIPELINES_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_tools() -> dict[str, Any]:
    """Load MCP tool definitions."""
    tools_file = TOOLS_DIR / "mcp_tools.json"
    import json
    with open(tools_file, encoding="utf-8") as f:
        return json.load(f)


def load_providers() -> dict[str, Any]:
    """Load provider configuration."""
    with open(PROVIDERS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def apply_specialization(
    agents: dict[str, Any],
    specialization: dict[str, str],
) -> None:
    """Apply specialization overrides to all agent profiles."""
    for agent in agents.values():
        if "specialization" not in agent:
            agent["specialization"] = {}
        for key, value in specialization.items():
            if key in agent["specialization"]:
                # Handle list vs string types
                current = agent["specialization"][key]
                if isinstance(current, list):
                    agent["specialization"][key] = [v.strip() for v in value.split(",")]
                else:
                    agent["specialization"][key] = value


def build_bundle(
    specialization: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the complete bundle."""
    agents = load_agent_profiles()
    pipelines = load_pipelines()
    tools = load_tools()
    providers = load_providers()

    if specialization:
        apply_specialization(agents, specialization)

    # Extract provider summary (without full model lists for bundle compactness)
    provider_summary = {}
    for name, pconfig in providers.get("providers", {}).items():
        provider_summary[name] = {
            "env_key": pconfig.get("env_key"),
            "base_url": pconfig.get("base_url"),
            "default_model": pconfig.get("default_model"),
            "local": pconfig.get("local", False),
        }

    return {
        "schema_version": "1.0",
        "meta": {
            "name": "job-booster-agents",
            "version": "1.0.0",
            "description": (
                "Portable agent profiles for job search automation. "
                "Field-agnostic — configure specialization for any industry."
            ),
            "agent_count": len(agents),
            "pipeline_count": len(pipelines.get("pipelines", {})),
            "tool_count": len(tools.get("tools", [])),
            "provider_count": len(provider_summary),
        },
        "specialization": specialization or {
            "field": "",
            "industry": "",
            "role_types": [],
            "skills_focus": [],
        },
        "agents": agents,
        "pipelines": pipelines.get("pipelines", {}),
        "tools": tools.get("tools", []),
        "providers": provider_summary,
        "provider_chains": providers.get("chains", {}),
        "defaults": providers.get("defaults", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundle agent profiles")
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=str(PROFILES_DIR / "bundle.yaml"),
        help="Output file path",
    )
    parser.add_argument(
        "--specialize", "-s",
        nargs="*",
        help="Specialization overrides: field=X industry=Y",
    )
    args = parser.parse_args()

    specialization = None
    if args.specialize:
        specialization = {}
        for item in args.specialize:
            if "=" in item:
                key, value = item.split("=", 1)
                specialization[key.strip()] = value.strip()

    bundle = build_bundle(specialization)

    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            bundle,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    print(f"Bundle written to {output_path}")
    print(f"  Agents: {bundle['meta']['agent_count']}")
    print(f"  Pipelines: {bundle['meta']['pipeline_count']}")
    print(f"  Tools: {bundle['meta']['tool_count']}")
    print(f"  Providers: {bundle['meta']['provider_count']}")

    if specialization:
        print(f"  Specialization: {specialization}")


if __name__ == "__main__":
    main()
