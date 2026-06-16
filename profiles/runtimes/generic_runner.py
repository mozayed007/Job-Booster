"""Generic LLM Runner — calls any OpenAI-compatible API.

This is the lowest-common-denominator runtime: it speaks the OpenAI
chat completions protocol, which every major provider supports
(OpenAI, Anthropic via proxy, Google via proxy, Groq, Together,
OpenRouter, Ollama, vLLM).

Usage:
    from profiles.runtimes.generic_runner import call_llm, run_agent

    # Direct LLM call
    result = await call_llm(
        system_prompt="You are a helpful assistant.",
        user_message="Hello!",
        model_string="openai:gpt-4o",
    )

    # Run an agent profile
    result = await run_agent(
        profile_name="resume-reviewer",
        inputs={"resume_text": "..."},
    )
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import yaml

from profiles.runtimes.security import ProfileNotAllowedError, validate_profile_name

PROFILES_DIR = Path(__file__).parent.parent
AGENTS_DIR = PROFILES_DIR / "agents"
PROVIDERS_FILE = PROFILES_DIR / "providers.yaml"


def _load_provider_config(model_string: str) -> dict[str, Any]:
    """Load provider config for a model string like 'openai:gpt-4o'."""
    with open(PROVIDERS_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    provider_name = model_string.split(":")[0] if ":" in model_string else ""
    providers = config.get("providers", {})
    provider = providers.get(provider_name, {})

    return {
        "base_url": provider.get("base_url", ""),
        "api_key_env": provider.get("env_key", ""),
        "model": model_string.split(":", 1)[1] if ":" in model_string else model_string,
    }


def _get_api_key(api_key_env: str) -> str:
    """Get API key from environment."""
    if not api_key_env:
        return ""
    return os.getenv(api_key_env, "")


def _build_headers(api_key: str, provider_name: str) -> dict[str, str]:
    """Build request headers based on provider."""
    headers = {
        "Content-Type": "application/json",
    }

    if not api_key:
        return headers

    # Anthropic uses x-api-key, everyone else uses Authorization
    if provider_name == "anthropic":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {api_key}"

    return headers


async def call_llm(
    system_prompt: str,
    user_message: str,
    model_string: str,
    fallbacks: list[str] | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    response_format: dict[str, Any] | None = None,
) -> str:
    """Call an LLM using the OpenAI-compatible chat completions API.

    Args:
        system_prompt: System message
        user_message: User message
        model_string: Model in "provider:model" format (e.g., "openai:gpt-4o")
        fallbacks: List of fallback model strings to try if primary fails
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        response_format: Optional response format (e.g., {"type": "json_object"})

    Returns:
        The LLM's response text

    Raises:
        Exception if all providers fail
    """
    all_models = [model_string] + (fallbacks or [])
    errors = []

    for model in all_models:
        try:
            return await _call_single(
                system_prompt=system_prompt,
                user_message=user_message,
                model_string=model,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
            )
        except Exception as e:
            errors.append(f"{model}: {e}")
            continue

    raise Exception("All LLM providers failed:\n" + "\n".join(errors))


async def _call_single(
    system_prompt: str,
    user_message: str,
    model_string: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    response_format: dict[str, Any] | None = None,
) -> str:
    """Call a single LLM provider."""
    provider_name = model_string.split(":")[0] if ":" in model_string else ""
    provider_config = _load_provider_config(model_string)

    base_url = provider_config["base_url"]
    model = provider_config["model"]
    api_key = _get_api_key(provider_config["api_key_env"])

    if not base_url:
        raise ValueError(f"No base URL configured for provider: {provider_name}")

    # Build the request
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = _build_headers(api_key, provider_name)

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    if response_format:
        payload["response_format"] = response_format

    # Make the request
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")

        data = response.json()

    # Extract response text
    choices = data.get("choices", [])
    if not choices:
        raise Exception("No choices in response")

    message = choices[0].get("message", {})
    content = message.get("content", "")

    if not content:
        raise Exception("Empty response content")

    return content


async def run_agent(
    profile_name: str,
    inputs: dict[str, Any],
    model_string: str | None = None,
    chain: str | None = None,
) -> str:
    """Run an agent profile with the given inputs.

    Args:
        profile_name: Agent profile name (kebab-case, e.g., "resume-reviewer")
        inputs: Input values matching the profile's I/O contract
        model_string: Explicit model to use (overrides chain resolution)
        chain: Provider chain name (default: from providers.yaml)

    Returns:
        The agent's response text
    """
    # Validate profile name against the declared allowlist and block
    # path traversal before touching the filesystem.
    try:
        validate_profile_name(profile_name)
    except ProfileNotAllowedError as e:
        raise ValueError(str(e)) from e

    # Load profile
    profile_path = AGENTS_DIR / f"{profile_name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")

    with open(profile_path, encoding="utf-8") as f:
        profile = yaml.safe_load(f)

    # Build user message from inputs
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
    system_prompt = profile.get("instructions", "")

    # Resolve model
    if model_string is None:
        from profiles.provider_resolver import resolve_chain

        model_string, fallbacks = resolve_chain(chain)
        if not model_string:
            raise Exception("No LLM provider available. Set an API key or start a local model.")
    else:
        fallbacks = []

    # Check if profile wants structured output
    response_format = None
    outputs = io_def.get("outputs", [])
    if outputs and any(o.get("type") == "object" or o.get("type") == "array" for o in outputs):
        response_format = {"type": "json_object"}

    return await call_llm(
        system_prompt=system_prompt,
        user_message=user_message,
        model_string=model_string,
        fallbacks=fallbacks,
        response_format=response_format,
    )
