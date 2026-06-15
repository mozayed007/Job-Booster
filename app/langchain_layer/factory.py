"""Model factory for the LangChain layer.

Builds a ``ChatLiteLLM`` instance that reuses the project's existing LiteLLM
configuration (provider detection, fallback chains, API keys) so the LangChain
and Pydantic AI layers are compared on orchestration, not model access.
"""

from langchain_litellm import ChatLiteLLM
from loguru import logger

from app.core.model_registry import get_litellm_model_string


def get_model_name() -> str:
    """Return the primary LiteLLM model string for the current environment."""
    return get_litellm_model_string()


def build_llm(model_name: str | None = None, temperature: float = 0.2) -> ChatLiteLLM:
    """Create a LangChain chat model backed by LiteLLM.

    Args:
        model_name: LiteLLM model string (e.g. ``gemini/gemini-3.1-flash-lite``).
            Defaults to the project's configured primary model.
        temperature: Sampling temperature.

    Returns:
        A configured ``ChatLiteLLM`` instance.
    """
    resolved = model_name or get_model_name()
    logger.debug(f"LangChain layer using model: {resolved}")
    return ChatLiteLLM(
        model=resolved,
        temperature=temperature,
        streaming=False,
    )
