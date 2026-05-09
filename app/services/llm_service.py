"""Core LLM service for direct text generation via LiteLLM.

For structured output / typed agents, use create_agent() from model_registry instead.
This service is for raw completion calls (analysis, freeform generation).
"""

from typing import Any, Optional

import litellm
from loguru import logger
from pydantic import BaseModel

from app.core.model_registry import get_registry


class LLMService:
    """Direct LLM completion service (wraps litellm.acompletion).

    For structured/typed output, use create_agent() from model_registry instead.
    """

    def __init__(self):
        self.registry = get_registry()
        self.chain = self.registry.resolve_chain()
        logger.info(f"LLMService: primary={self.chain.primary_model_string}")

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        response_model: Optional[type[BaseModel]] = None,
    ) -> str:
        """Generate text with automatic fallback."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        all_models = [self.chain.primary_model_string] + self.chain.fallback_model_strings
        last_error = None

        for model in all_models:
            try:
                kwargs: dict[str, Any] = {"model": model, "messages": messages}
                if response_model:
                    kwargs["response_format"] = response_model
                response = await litellm.acompletion(**kwargs)
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                last_error = e

        raise RuntimeError(f"All models failed. Last error: {last_error}")

    async def generate_structured(
        self,
        prompt: str,
        system: Optional[str] = None,
    ) -> str:
        """Generate text optimized for structured data extraction."""
        json_system = (
            (system + "\n\n" if system else "")
            + "You MUST respond with valid JSON only. No markdown, no explanation, just the JSON object."
        )
        return await self.generate(prompt, system=json_system)
