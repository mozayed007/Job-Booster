"""Unified Model Registry — single source of truth for all LLM configuration.

Auto-detects available providers, builds fallback chains, creates agents.
Every agent and service in the app gets its model from here.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any

from loguru import logger
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from app.core.config import settings

# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    NEBIUS = "nebius"
    GROQ = "groq"
    TOGETHER = "together"
    VLLM = "vllm"


# Pydantic AI uses ``provider:model`` while LiteLLM uses ``provider/model``.
# Map the few providers whose LiteLLM slug differs from the Pydantic AI name.
_PROVIDER_TO_LITELLM: dict[str, str] = {
    Provider.GOOGLE: "gemini",
}


def _to_litellm(model_string: str) -> str:
    """Convert a Pydantic AI model string to a LiteLLM model string.

    If the input already looks like a LiteLLM string (contains ``/`` or has no
    ``:``), it is returned unchanged.
    """
    if "/" in model_string or ":" not in model_string:
        return model_string
    provider, _, model = model_string.partition(":")
    return f"{_PROVIDER_TO_LITELLM.get(provider, provider)}/{model}"


@dataclass
class ProviderInfo:
    name: Provider
    available: bool = False
    model_string: str = ""
    detected_via: str = ""


def _detect_env_providers() -> list[ProviderInfo]:
    """Detect cloud providers from environment variables (no network I/O)."""
    providers = []

    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    providers.append(
        ProviderInfo(
            name=Provider.OPENAI,
            available=has_openai,
            model_string="openai:gpt-4o",
            detected_via="OPENAI_API_KEY" if has_openai else "",
        )
    )

    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    providers.append(
        ProviderInfo(
            name=Provider.ANTHROPIC,
            available=has_anthropic,
            model_string="anthropic:claude-sonnet-4-5",
            detected_via="ANTHROPIC_API_KEY" if has_anthropic else "",
        )
    )

    has_google = bool(
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_GEMINI_API_KEY")
    )
    providers.append(
        ProviderInfo(
            name=Provider.GOOGLE,
            available=has_google,
            model_string="google:gemini-3.1-flash-lite",
            detected_via="GEMINI_API_KEY" if has_google else "",
        )
    )

    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
    providers.append(
        ProviderInfo(
            name=Provider.OPENROUTER,
            available=has_openrouter,
            model_string="openrouter:anthropic/claude-sonnet-4-5",
            detected_via="OPENROUTER_API_KEY" if has_openrouter else "",
        )
    )

    has_groq = bool(os.getenv("GROQ_API_KEY"))
    providers.append(
        ProviderInfo(
            name=Provider.GROQ,
            available=has_groq,
            model_string="groq:llama-3.3-70b-versatile",
            detected_via="GROQ_API_KEY" if has_groq else "",
        )
    )

    has_together = bool(os.getenv("TOGETHER_API_KEY"))
    providers.append(
        ProviderInfo(
            name=Provider.TOGETHER,
            available=has_together,
            model_string="together:meta-llama/Llama-3-70b-chat-hf",
            detected_via="TOGETHER_API_KEY" if has_together else "",
        )
    )

    return providers


async def _detect_local_providers_async() -> list[ProviderInfo]:
    """Detect local providers via HTTP probes (runs off the event loop)."""
    providers = []

    try:
        import httpx

        ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        vllm_base = os.getenv("VLLM_BASE_URL", "http://localhost:8001")

        async with httpx.AsyncClient(timeout=1.0) as client:
            ollama_available = False
            try:
                resp = await client.get(f"{ollama_base}/api/tags")
                ollama_available = resp.status_code < 500
            except Exception:
                pass

            vllm_available = False
            try:
                resp = await client.get(f"{vllm_base}/health")
                vllm_available = resp.status_code < 500
            except Exception:
                pass
    except ImportError:
        ollama_available = False
        vllm_available = False

    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    providers.append(
        ProviderInfo(
            name=Provider.OLLAMA,
            available=ollama_available,
            model_string=f"ollama:{ollama_model}",
            detected_via="localhost:11434 ping" if ollama_available else "",
        )
    )

    vllm_model = os.getenv("VLLM_MODEL", "default")
    providers.append(
        ProviderInfo(
            name=Provider.VLLM,
            available=vllm_available,
            model_string=f"openai:{vllm_model}",
            detected_via=f"{vllm_base} ping" if vllm_available else "",
        )
    )

    return providers


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class ModelSettings(BaseSettings):
    """All model-related configuration, loaded from environment."""

    # Explicit overrides (highest priority)
    default_model: str | None = None
    fallback_model: str | None = None

    # Provider API keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    google_gemini_api_key: str | None = None
    openrouter_api_key: str | None = None
    groq_api_key: str | None = None
    together_api_key: str | None = None

    # Local model config
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    vllm_base_url: str = "http://localhost:8001"
    vllm_model: str = "default"

    # Behavior
    prefer_local: bool = False
    litellm_verbose: bool = False
    litellm_cache: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_model_settings() -> ModelSettings:
    return ModelSettings()


# ---------------------------------------------------------------------------
# Registry — the core
# ---------------------------------------------------------------------------


@dataclass
class ModelChain:
    """Resolved model chain with primary + fallback."""

    primary_model_string: str
    fallback_model_strings: list[str] = field(default_factory=list)
    primary_provider: Provider | None = None
    all_providers: list[ProviderInfo] = field(default_factory=list)


class ModelRegistry:
    """Central registry. Call `get_registry()` to get the singleton."""

    def __init__(self):
        self.settings = get_model_settings()
        # Phase 1: detect cloud providers from env vars (no network I/O)
        self.providers = _detect_env_providers()
        self._chain: ModelChain | None = None
        self._local_probed = False
        self._configure_env()
        self._configure_litellm()
        self._log_status()

    async def probe_local_providers(self):
        """Phase 2: probe local providers (Ollama, vLLM) via HTTP.
        Call this from an async context (e.g., lifespan handler) to avoid
        blocking the event loop on startup.
        """
        if self._local_probed:
            return
        local = await _detect_local_providers_async()
        self.providers.extend(local)
        self._local_probed = True
        self._chain = None  # invalidate cached chain
        self._log_status()

    def _configure_env(self):
        """Propagate settings to environment variables."""
        s = self.settings
        mappings = [
            (s.openai_api_key, "OPENAI_API_KEY"),
            (s.anthropic_api_key, "ANTHROPIC_API_KEY"),
            (s.gemini_api_key or s.google_api_key or s.google_gemini_api_key, "GEMINI_API_KEY"),
            (s.openrouter_api_key, "OPENROUTER_API_KEY"),
            (s.groq_api_key, "GROQ_API_KEY"),
            (s.together_api_key, "TOGETHER_API_KEY"),
        ]
        for val, key in mappings:
            if val and not os.getenv(key):
                os.environ[key] = val

        # Set OLLAMA_API_BASE regardless of availability (local probe is async)
        os.environ["OLLAMA_API_BASE"] = s.ollama_base_url

    def _configure_litellm(self):
        """Configure LiteLLM global settings."""
        try:
            import litellm

            # Only enable verbose logging in debug mode to avoid leaking
            # prompts, API keys, or response contents in production logs.
            if settings.DEBUG:
                litellm.set_verbose = self.settings.litellm_verbose
            if self.settings.litellm_cache:
                litellm.cache = litellm.Cache()

            # Only enable the Logfire callback when a token is actually
            # available; otherwise LiteLLM raises during every completion.
            if os.getenv("LOGFIRE_TOKEN"):
                try:
                    litellm.success_callback = ["logfire"]
                    litellm.failure_callback = ["logfire"]
                except Exception:
                    pass

            # Enable Langfuse OTEL callback when credentials are present.
            try:
                from app.core.langfuse_setup import init_langfuse

                init_langfuse()
            except Exception:
                pass
        except ImportError:
            pass

    def _is_available(self, provider: Provider) -> bool:
        return any(p.name == provider and p.available for p in self.providers)

    def _get_provider(self, provider: Provider) -> ProviderInfo | None:
        for p in self.providers:
            if p.name == provider:
                return p
        return None

    def _log_status(self):
        available = [p.name.value for p in self.providers if p.available]
        unavailable = [p.name.value for p in self.providers if not p.available]
        logger.info(f"ModelRegistry: available={available}, unavailable={unavailable}")

    # -----------------------------------------------------------------------
    # Build the model chain
    # -----------------------------------------------------------------------

    def resolve_chain(self) -> ModelChain:
        """Build the model chain based on settings + auto-detection."""
        if self._chain:
            return self._chain

        s = self.settings
        chain = ModelChain(primary_model_string="", all_providers=self.providers)

        # 1. Explicit override (highest priority)
        if s.default_model:
            chain.primary_model_string = s.default_model
            chain.primary_provider = None  # user-specified
            # Still populate fallbacks from available providers
            chain.fallback_model_strings = self._collect_fallbacks(exclude_model=s.default_model)
        elif s.prefer_local:
            # Prefer local first
            chain = self._build_local_first_chain()
        else:
            # Cloud-first with local fallback
            chain = self._build_cloud_first_chain()

        # 2. Explicit fallback override
        if s.fallback_model:
            chain.fallback_model_strings.insert(0, s.fallback_model)

        self._chain = chain
        logger.info(
            f"Model chain: primary={chain.primary_model_string}, "
            f"fallbacks={chain.fallback_model_strings}"
        )
        return chain

    def _build_cloud_first_chain(self) -> ModelChain:
        """Cloud providers first, local as last resort."""
        cloud_order = [
            Provider.GOOGLE,
            Provider.OPENAI,
            Provider.ANTHROPIC,
            Provider.GROQ,
            Provider.OPENROUTER,
            Provider.TOGETHER,
        ]
        local_order = [Provider.OLLAMA, Provider.VLLM]

        primary = self._first_available(cloud_order)
        fallbacks = []

        # Remaining cloud as fallbacks
        for p in cloud_order:
            if p != primary and self._is_available(p):
                info = self._get_provider(p)
                if info:
                    fallbacks.append(info.model_string)

        # Local as last resort
        for p in local_order:
            if self._is_available(p):
                info = self._get_provider(p)
                if info:
                    fallbacks.append(info.model_string)

        primary_info = self._get_provider(primary) if primary else None
        return ModelChain(
            primary_model_string=primary_info.model_string
            if primary_info
            else "google:gemini-3.1-flash-lite",
            fallback_model_strings=fallbacks,
            primary_provider=primary,
        )

    def _build_local_first_chain(self) -> ModelChain:
        """Local models first, cloud as fallback."""
        local_order = [Provider.OLLAMA, Provider.VLLM]
        cloud_order = [
            Provider.GOOGLE,
            Provider.OPENAI,
            Provider.ANTHROPIC,
            Provider.GROQ,
            Provider.OPENROUTER,
        ]

        primary = self._first_available(local_order)
        fallbacks = []

        if not primary:
            return self._build_cloud_first_chain()

        # Remaining local
        for p in local_order:
            if p != primary and self._is_available(p):
                info = self._get_provider(p)
                if info:
                    fallbacks.append(info.model_string)

        # Cloud as fallback
        for p in cloud_order:
            if self._is_available(p):
                info = self._get_provider(p)
                if info:
                    fallbacks.append(info.model_string)

        primary_info = self._get_provider(primary)
        return ModelChain(
            primary_model_string=primary_info.model_string if primary_info else "ollama:llama3.2",
            fallback_model_strings=fallbacks,
            primary_provider=primary,
        )

    def _first_available(self, providers: list[Provider]) -> Provider | None:
        for p in providers:
            if self._is_available(p):
                return p
        return None

    def _collect_fallbacks(self, exclude_model: str = "") -> list[str]:
        """Collect model strings from all available providers, excluding a specific model."""
        fallbacks = []
        priority_order = [
            Provider.GOOGLE,
            Provider.OPENAI,
            Provider.ANTHROPIC,
            Provider.GROQ,
            Provider.OPENROUTER,
            Provider.TOGETHER,
            Provider.OLLAMA,
            Provider.VLLM,
        ]
        for p in priority_order:
            if self._is_available(p):
                info = self._get_provider(p)
                if info and info.model_string != exclude_model:
                    fallbacks.append(info.model_string)
        return fallbacks

    # -----------------------------------------------------------------------
    # Public API — what the rest of the app uses
    # -----------------------------------------------------------------------

    def get_model_string(self) -> str:
        """Get the primary model string for Pydantic AI."""
        return self.resolve_chain().primary_model_string

    def get_litellm_model_string(self) -> str:
        """Get the primary model string formatted for LiteLLM / LangChain."""
        return _to_litellm(self.get_model_string())

    def get_fallback_model_strings(self) -> list[str]:
        return self.resolve_chain().fallback_model_strings

    def get_model(self):
        """Get a Pydantic AI model instance (with fallback chain if multiple available).

        Returns a model object ready to pass to Agent(model=...).
        """
        try:
            from pydantic_ai.models.fallback import FallbackModel

            chain = self.resolve_chain()

            if not chain.fallback_model_strings:
                # Single model, no fallback needed
                return chain.primary_model_string

            # Build FallbackModel with primary + all fallbacks
            all_models = [chain.primary_model_string] + chain.fallback_model_strings
            return FallbackModel(*all_models)

        except ImportError:
            logger.warning("pydantic-ai FallbackModel not available, using string model")
            return self.get_model_string()

    def create_agent(
        self,
        output_type: type[BaseModel] | type | None = None,
        system_prompt: str = "",
        retries: int = 2,
        **kwargs,
    ):
        """Create a Pydantic AI Agent with the configured model + fallbacks.

        This is THE factory every agent in the app should use.

        Args:
            output_type: Pydantic model for structured output (or None for plain text).
            system_prompt: System prompt / instructions.
            retries: Number of retries on failure.
            **kwargs: Additional kwargs passed to Agent().

        Returns:
            Configured Agent instance.
        """
        from pydantic_ai import Agent

        model = self.get_model()

        agent_kwargs = {
            "model": model,
            "instructions": system_prompt,
            "retries": retries,
        }
        if output_type is not None:
            agent_kwargs["output_type"] = output_type
        agent_kwargs.update(kwargs)

        return Agent(**agent_kwargs)

    async def health_check(self) -> dict[str, Any]:
        """Check which providers are reachable with a minimal request."""
        results = {}
        for provider in self.providers:
            if not provider.available:
                results[provider.name.value] = {"status": "unavailable", "reason": "no credentials"}
                continue

            try:
                from pydantic_ai import Agent

                agent = Agent(provider.model_string)
                result = await agent.run("Say OK", model_settings={"max_tokens": 5})
                results[provider.name.value] = {
                    "status": "ok",
                    "model": provider.model_string,
                    "response_preview": str(result.output)[:50],
                }
            except Exception as e:
                results[provider.name.value] = {
                    "status": "error",
                    "model": provider.model_string,
                    "error": str(e)[:200],
                }

        return results

    def get_status(self) -> dict[str, Any]:
        """Return current registry status (sync, no network calls)."""
        chain = self.resolve_chain()
        return {
            "primary": chain.primary_model_string,
            "fallbacks": chain.fallback_model_strings,
            "providers": {
                p.name.value: {
                    "available": p.available,
                    "model": p.model_string,
                    "detected_via": p.detected_via,
                }
                for p in self.providers
            },
            "prefer_local": self.settings.prefer_local,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    """Get or create the singleton ModelRegistry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


# ---------------------------------------------------------------------------
# Convenience shortcuts (what the rest of the app actually calls)
# ---------------------------------------------------------------------------


def get_model_string() -> str:
    """Get primary model string. Replaces old get_pydantic_ai_model()."""
    return get_registry().get_model_string()


def get_litellm_model_string() -> str:
    """Get primary model string formatted for LiteLLM / LangChain."""
    return get_registry().get_litellm_model_string()


def get_model():
    """Get Pydantic AI model instance with fallback chain."""
    return get_registry().get_model()


def create_agent(
    output_type=None,
    system_prompt: str = "",
    retries: int = 2,
    **kwargs,
):
    """Create a configured Pydantic AI Agent. THE factory function."""
    return get_registry().create_agent(
        output_type=output_type,
        system_prompt=system_prompt,
        retries=retries,
        **kwargs,
    )


async def health_check() -> dict[str, Any]:
    """Run health check on all providers."""
    return await get_registry().health_check()


def get_status() -> dict[str, Any]:
    """Get registry status (sync)."""
    return get_registry().get_status()


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


def get_pydantic_ai_model(settings=None) -> str:
    """Backward-compatible alias. Deprecated — use get_model_string()."""
    return get_model_string()


def get_model_name(settings=None) -> str:
    """Backward-compatible alias. Deprecated — use get_model_string()."""
    return get_model_string()


def get_llm_settings():
    """Backward-compatible alias. Deprecated — use get_registry().settings."""
    return get_registry().settings


def init_ai_stack():
    """Initialize the AI stack. Call once at startup."""
    get_registry()
    try:
        import logfire

        logfire.configure(
            send_to_logfire="if-token-present",
        )
        logfire.instrument_httpx()
        logfire.info("Job_Booster AI stack initialized")
    except Exception:
        pass
