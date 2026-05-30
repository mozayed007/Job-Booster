"""Portable Provider Resolver — detects available LLM providers on any platform.

Reads from profiles/providers.yaml and checks environment variables and
local endpoints to determine which providers are available.

Usage:
    from profiles.provider_resolver import resolve_providers, get_model_string

    providers = resolve_providers()
    model = get_model_string(chain="cloud_first")
"""

from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


PROFILES_DIR = Path(__file__).parent
PROVIDERS_FILE = PROFILES_DIR / "providers.yaml"


@dataclass
class ResolvedProvider:
    """A provider that's available on this machine."""
    name: str
    available: bool = False
    model_string: str = ""
    base_url: str = ""
    default_model: str = ""
    detected_via: str = ""
    local: bool = False
    models: list[dict[str, Any]] = field(default_factory=list)


def _check_env_key(key: str, alt_keys: list[str] | None = None) -> tuple[bool, str]:
    """Check if an env var is set."""
    if key and os.getenv(key):
        return True, key
    if alt_keys:
        for alt in alt_keys:
            if os.getenv(alt):
                return True, alt
    return False, ""


def _check_local_endpoint(url: str, timeout: int = 3) -> bool:
    """Check if a local endpoint is reachable."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def load_providers_config() -> dict[str, Any]:
    """Load providers.yaml."""
    with open(PROVIDERS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_providers(
    config: dict[str, Any] | None = None,
) -> list[ResolvedProvider]:
    """Detect which providers are available on this machine.

    Args:
        config: Optional pre-loaded providers.yaml content

    Returns:
        List of ResolvedProvider with availability status
    """
    if config is None:
        config = load_providers_config()

    providers_config = config.get("providers", {})
    resolved: list[ResolvedProvider] = []

    for name, pconfig in providers_config.items():
        env_key = pconfig.get("env_key")
        alt_keys = pconfig.get("alt_env_keys", [])
        base_url = pconfig.get("base_url", "")
        local = pconfig.get("local", False)
        default_model = pconfig.get("default_model", "")
        models = pconfig.get("models", [])
        health_check = pconfig.get("health_check")

        available = False
        detected_via = ""

        if local:
            # Check health endpoint for local providers
            check_url = health_check or base_url
            if check_url:
                available = _check_local_endpoint(check_url)
                detected_via = f"local endpoint: {check_url}"
        elif env_key:
            available, detected_via = _check_env_key(env_key, alt_keys)

        model_string = f"{name}:{default_model}" if default_model else ""

        resolved.append(ResolvedProvider(
            name=name,
            available=available,
            model_string=model_string,
            base_url=base_url,
            default_model=default_model,
            detected_via=detected_via,
            local=local,
            models=models,
        ))

    return resolved


def get_chain(
    chain_name: str | None = None,
    config: dict[str, Any] | None = None,
) -> list[str]:
    """Get an ordered provider chain by name.

    Args:
        chain_name: Chain name from providers.yaml (default: defaults.chain)
        config: Optional pre-loaded config

    Returns:
        Ordered list of provider names
    """
    if config is None:
        config = load_providers_config()

    if chain_name is None:
        chain_name = config.get("defaults", {}).get("chain", "cloud_first")

    chains = config.get("chains", {})
    chain = chains.get(chain_name, {})
    return chain.get("providers", [])


def resolve_chain(
    chain_name: str | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """Resolve the first available model from a fallback chain.

    Args:
        chain_name: Chain name (default: from providers.yaml defaults)
        config: Optional pre-loaded config

    Returns:
        Tuple of (model_string, [fallback_model_strings])
        model_string format: "provider:model" (e.g., "openai:gpt-4o")
    """
    if config is None:
        config = load_providers_config()

    chain_order = get_chain(chain_name, config)
    available = resolve_providers(config)

    available_map = {p.name: p for p in available if p.available}

    primary = None
    fallbacks = []

    for provider_name in chain_order:
        provider = available_map.get(provider_name)
        if provider and provider.model_string:
            if primary is None:
                primary = provider.model_string
            else:
                fallbacks.append(provider.model_string)

    if primary is None:
        # Last resort: try anything available
        for p in available:
            if p.available and p.model_string:
                primary = p.model_string
                break

    return primary or "", fallbacks


def get_model_string(chain_name: str | None = None) -> str:
    """Get a single model string for the first available provider.

    Returns:
        Model string in "provider:model" format, or empty string if none available
    """
    model, _ = resolve_chain(chain_name)
    return model


def get_provider_info() -> dict[str, Any]:
    """Get a summary of all providers and their availability.

    Returns:
        Dict with provider status, recommended chain, and model strings
    """
    config = load_providers_config()
    available = resolve_providers(config)
    primary, fallbacks = resolve_chain(config=config)
    defaults = config.get("defaults", {})

    return {
        "providers": {
            p.name: {
                "available": p.available,
                "model_string": p.model_string,
                "local": p.local,
                "detected_via": p.detected_via,
            }
            for p in available
        },
        "recommended": {
            "primary": primary,
            "fallbacks": fallbacks,
            "chain": defaults.get("chain", "cloud_first"),
        },
        "defaults": defaults,
    }
