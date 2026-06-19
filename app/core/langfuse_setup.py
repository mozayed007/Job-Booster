"""Langfuse observability setup — optional, like Logfire.

Call :func:`init_langfuse` once at startup (from ``ModelRegistry._configure_litellm``).
If ``LANGFUSE_PUBLIC_KEY`` and ``LANGFUSE_SECRET_KEY`` are set, the Langfuse client
is initialized with OTEL span processing so every LLM call routed through Pydantic AI
or LiteLLM is traced automatically.

For LangGraph-specific tracing, use :func:`build_langgraph_config` to obtain a
config dict carrying trace metadata, ready to pass to ``graph.ainvoke(..., config=...)``.
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger

_langfuse_client: Any = None


def _reset_langfuse_client() -> None:
    """Reset the global client. For testing only."""
    global _langfuse_client
    _langfuse_client = None


def _langfuse_credentials(
    public_key: str | None = None,
    secret_key: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve Langfuse credentials from args or environment."""
    pk = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
    sk = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
    return pk, sk


def is_langfuse_enabled(public_key: str | None = None, secret_key: str | None = None) -> bool:
    """Return True when Langfuse credentials are available."""
    pk, sk = _langfuse_credentials(public_key, secret_key)
    return bool(pk and sk)


def get_langfuse_client():
    """Return the initialized Langfuse client, or None."""
    return _langfuse_client


def init_langfuse() -> None:
    """Initialize the Langfuse client with OTEL span processing when credentials are present.

    Safe to call even when ``langfuse`` is not installed — it silently skips.
    Idempotent: repeated calls never create a second client.
    """
    global _langfuse_client

    if _langfuse_client is not None:
        return

    if not is_langfuse_enabled():
        return

    host = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    try:
        from langfuse import Langfuse

        pk, sk = _langfuse_credentials()
        _langfuse_client = Langfuse(
            public_key=pk,
            secret_key=sk,
            base_url=host,
        )
        logger.info(f"Langfuse client initialized (host={host})")
    except ImportError:
        logger.debug("langfuse not installed; skipping initialization")
    except Exception as exc:
        logger.debug(f"Failed to initialize Langfuse: {exc}")


def build_langgraph_config(
    pipeline_name: str,
    *,
    metadata: dict[str, Any] | None = None,
    public_key: str | None = None,
    secret_key: str | None = None,
) -> dict[str, Any] | None:
    """Build a LangGraph config dict carrying trace metadata for Langfuse.

    Returns ``None`` when Langfuse is not configured, so callers can pass the
    result straight to ``graph.ainvoke(state, config=...)`` without branching.

    The ``metadata`` carries ``langfuse_session_id`` and ``pipeline`` so Langfuse
    groups all spans of a pipeline run under one named session.
    """
    if not is_langfuse_enabled(public_key, secret_key):
        return None

    merged: dict[str, Any] = {
        "langfuse_session_id": pipeline_name,
        "pipeline": pipeline_name,
    }
    if metadata:
        merged.update(metadata)

    return {"metadata": merged}
