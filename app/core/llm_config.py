"""LLM configuration — delegates to ModelRegistry.

This module exists for backward compatibility. New code should import from
app.core.model_registry directly.
"""

# Re-export everything from model_registry
from app.core.model_registry import (
    ModelRegistry,
    ModelSettings,
    create_agent,
    get_llm_settings,
    get_model,
    get_model_name,
    get_model_string,
    get_pydantic_ai_model,
    get_registry,
    get_status,
    health_check,
    init_ai_stack,
)

__all__ = [
    "get_registry",
    "get_model_string",
    "get_model",
    "create_agent",
    "health_check",
    "get_status",
    "get_pydantic_ai_model",
    "get_model_name",
    "get_llm_settings",
    "init_ai_stack",
    "ModelSettings",
    "ModelRegistry",
]
