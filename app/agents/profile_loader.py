"""Profile Loader — makes profiles/ the single source of truth for agents.

This module replaces the YAML + dispatch logic in base_agent.py with a
profile-driven approach. It reads from profiles/agents/*.yaml and builds
agent instances, preserving backward compatibility with the existing
BaseAgent interface.

Usage:
    from app.agents.profile_loader import load_agents_from_profiles

    agents = load_agents_from_profiles()
    job_finder = agents["job_finder"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

PROFILES_DIR = Path(__file__).parent.parent.parent / "profiles"
AGENTS_DIR = PROFILES_DIR / "agents"


def _kebab_to_snake(name: str) -> str:
    """Convert kebab-case to snake_case for backward compatibility."""
    return name.replace("-", "_")


def _snake_to_kebab(name: str) -> str:
    """Convert snake_case to kebab-case."""
    return name.replace("_", "-")


@dataclass
class ProfileAgentConfig:
    """Agent config derived from a profile YAML."""

    key: str  # snake_case key (e.g., "job_finder")
    name: str
    description: str
    enabled: bool = True
    skill_content: str = ""
    system_prompt: str = ""
    model_retries: int = 2
    tools_required: list[str] = field(default_factory=list)
    tools_optional: list[str] = field(default_factory=list)
    io_inputs: list[dict[str, Any]] = field(default_factory=list)
    io_outputs: list[dict[str, Any]] = field(default_factory=list)
    specialization: dict[str, Any] = field(default_factory=dict)
    adapters: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_profile(cls, profile: dict[str, Any]) -> ProfileAgentConfig:
        """Build config from a parsed profile YAML."""
        meta = profile.get("meta", {})
        requirements = profile.get("requirements", {})
        io_def = profile.get("io", {})
        tools = requirements.get("tools", [])

        required_tools = [t["name"] for t in tools if not t.get("optional")]
        optional_tools = [t["name"] for t in tools if t.get("optional")]

        return cls(
            key=_kebab_to_snake(meta.get("name", "")),
            name=meta.get("display_name", meta.get("name", "")),
            description=meta.get("description", ""),
            enabled=True,
            skill_content=profile.get("instructions", ""),
            system_prompt=profile.get("instructions", ""),
            model_retries=2,
            tools_required=required_tools,
            tools_optional=optional_tools,
            io_inputs=io_def.get("inputs", []),
            io_outputs=io_def.get("outputs", []),
            specialization=profile.get("specialization", {}),
            adapters=profile.get("adapters", {}),
        )


def load_profiles(
    profiles_dir: Path | None = None,
    agent_filter: list[str] | None = None,
) -> dict[str, ProfileAgentConfig]:
    """Load all agent profiles from YAML files.

    Args:
        profiles_dir: Path to profiles/ directory (defaults to project profiles/)
        agent_filter: Optional list of agent keys to load (snake_case or kebab-case)

    Returns:
        Dict mapping snake_case agent keys to ProfileAgentConfig
    """
    if profiles_dir is None:
        profiles_dir = AGENTS_DIR

    if not profiles_dir.exists():
        logger.warning(f"Profiles directory not found: {profiles_dir}")
        return {}

    configs: dict[str, ProfileAgentConfig] = {}

    for path in sorted(profiles_dir.glob("*.yaml")):
        try:
            with open(path, encoding="utf-8") as f:
                profile = yaml.safe_load(f)

            config = ProfileAgentConfig.from_profile(profile)

            # Filter if requested
            if agent_filter:
                # Accept both snake_case and kebab-case
                filter_set = (
                    set(agent_filter)
                    | {_snake_to_kebab(k) for k in agent_filter}
                    | {_kebab_to_snake(k) for k in agent_filter}
                )
                if config.key not in filter_set and path.stem not in filter_set:
                    continue

            configs[config.key] = config

        except Exception as e:
            logger.error(f"Failed to load profile {path}: {e}")

    return configs


def get_profile_config(key: str) -> ProfileAgentConfig | None:
    """Get a single agent profile config by key.

    Args:
        key: Agent key (snake_case like 'job_finder' or kebab-case like 'job-finder')

    Returns:
        ProfileAgentConfig or None if not found
    """
    configs = load_profiles(agent_filter=[key])
    return configs.get(_kebab_to_snake(key))


def list_available_agents() -> list[dict[str, str | list[str]]]:
    """List all available agents with metadata.

    Returns:
        List of dicts with key, name, description
    """
    configs = load_profiles()
    return [
        {
            "key": key,
            "name": config.name,
            "description": config.description,
            "tools_required": config.tools_required,
            "tools_optional": config.tools_optional,
        }
        for key, config in configs.items()
    ]


def load_pipelines(profiles_dir: Path | None = None) -> dict[str, Any]:
    """Load pipeline definitions from profiles/pipelines.yaml.

    Returns:
        Dict of pipeline configs
    """
    if profiles_dir is None:
        profiles_dir = PROFILES_DIR

    pipelines_path = profiles_dir / "pipelines.yaml"
    if not pipelines_path.exists():
        logger.warning(f"Pipelines file not found: {pipelines_path}")
        return {}

    with open(pipelines_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    pipelines = data.get("pipelines", {})
    return pipelines if isinstance(pipelines, dict) else {}
