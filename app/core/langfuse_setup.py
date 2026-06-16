"""Langfuse observability setup — optional, like Logfire.

Call :func:`init_langfuse` once at startup (from ``ModelRegistry._configure_litellm``).
If ``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``, and ``LANGFUSE_BASE_URL`` are all
set, the LiteLLM ``langfuse_otel`` callback is enabled automatically.

For LangGraph-specific tracing, use :func:`get_langfuse_handler` to obtain a
``CallbackHandler`` to pass via ``config={"callbacks": [handler]}``.
"""

from __future__ import annotations

import os

from loguru import logger


def init_langfuse() -> None:
    """Enable the LiteLLM ``langfuse_otel`` callback when credentials are present.

    Safe to call even when ``langfuse`` is not installed — it silently skips.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    if not (public_key and secret_key):
        return

    try:
        import litellm

        if "langfuse_otel" not in litellm.callbacks:
            litellm.callbacks.append("langfuse_otel")
            logger.info(f"Langfuse OTEL callback enabled (host={host})")
    except ImportError:
        logger.debug("langfuse not installed; skipping OTEL callback")
    except Exception as exc:
        logger.debug(f"Failed to enable Langfuse OTEL callback: {exc}")


def get_langfuse_handler():
    """Return a LangChain ``CallbackHandler`` for LangGraph tracing, or ``None``.

    The handler is only created when Langfuse credentials are available.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not (public_key and secret_key):
        return None

    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()
    except ImportError:
        return None
    except Exception as exc:
        logger.debug(f"Failed to create Langfuse CallbackHandler: {exc}")
        return None
