"""Langfuse observability setup — optional, like Logfire.

Call :func:`init_langfuse` once at startup (from ``ModelRegistry._configure_litellm``).
If ``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``, and ``LANGFUSE_BASE_URL`` are all
set, the LiteLLM ``langfuse_otel`` callback is enabled automatically so every LLM
call routed through LiteLLM (Pydantic AI and ``ChatLiteLLM``) is traced.

For LangGraph-specific tracing, use :func:`build_langgraph_config` to obtain a
config dict carrying a Langfuse ``CallbackHandler`` plus trace metadata, ready to
pass to ``graph.ainvoke(..., config=...)``.
"""

from __future__ import annotations

import os
from typing import Any

from loguru import logger


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


def init_langfuse() -> None:
    """Enable the LiteLLM ``langfuse_otel`` callback when credentials are present.

    Safe to call even when ``langfuse`` is not installed — it silently skips.
    Idempotent: repeated calls never append a second callback.
    """
    if not is_langfuse_enabled():
        return

    host = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    try:
        import litellm

        if "langfuse_otel" not in litellm.callbacks:
            litellm.callbacks.append("langfuse_otel")
            logger.info(f"Langfuse OTEL callback enabled (host={host})")
    except ImportError:
        logger.debug("litellm not installed; skipping Langfuse OTEL callback")
    except Exception as exc:
        logger.debug(f"Failed to enable Langfuse OTEL callback: {exc}")


def get_langfuse_handler(
    public_key: str | None = None,
    secret_key: str | None = None,
):
    """Return a LangChain ``CallbackHandler`` for LangGraph tracing, or ``None``.

    The handler is only created when Langfuse credentials are available (from
    args or environment). Passing ``public_key``/``secret_key`` explicitly avoids
    relying on env vars being set at call time.
    """
    if not is_langfuse_enabled(public_key, secret_key):
        return None

    try:
        from langfuse.langchain import CallbackHandler

        pk, _ = _langfuse_credentials(public_key, secret_key)
        return CallbackHandler(public_key=pk)
    except ImportError:
        return None
    except Exception as exc:
        logger.debug(f"Failed to create Langfuse CallbackHandler: {exc}")
        return None


def build_langgraph_config(
    pipeline_name: str,
    *,
    metadata: dict[str, Any] | None = None,
    public_key: str | None = None,
    secret_key: str | None = None,
) -> dict[str, Any] | None:
    """Build a LangGraph config dict carrying a Langfuse handler + trace metadata.

    Returns ``None`` when Langfuse is not configured, so callers can pass the
    result straight to ``graph.ainvoke(state, config=...)`` without branching.

    The ``metadata`` carries ``langfuse_session_id`` and ``pipeline`` so Langfuse
    groups all spans of a pipeline run under one named session.
    """
    handler = get_langfuse_handler(public_key=public_key, secret_key=secret_key)
    if handler is None:
        return None

    merged: dict[str, Any] = {
        "langfuse_session_id": pipeline_name,
        "pipeline": pipeline_name,
    }
    if metadata:
        merged.update(metadata)

    return {"callbacks": [handler], "metadata": merged}
