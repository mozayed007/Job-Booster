"""Core LLM service for Job_Booster application.

This module handles interactions with the Large Language Model (Google Gemini via ADK)
for tasks like parsing, analysis, and content generation.
"""

import json
import os
from typing import Any, Dict, List, Optional

from loguru import logger

from app.core.config import settings


class LLMService:
    """Service for interacting with the configured LLM (Google Gemini via ADK)."""

    def __init__(self):
        """Initialize the LLM client using Google ADK."""
        self._agent = None
        self._runner = None
        self._session_service = None
        self._model = settings.GEMINI_MODEL
        self._api_key = settings.GOOGLE_GEMINI_API_KEY

        if not self._api_key:
            logger.warning(
                "GOOGLE_GEMINI_API_KEY is not set. LLMService will run in mock mode."
            )
        else:
            self._initialize_adk()

    def _initialize_adk(self) -> None:
        """Set up the underlying Google ADK agent and runner."""
        try:
            from google.adk.agents import Agent
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService

            self._session_service = InMemorySessionService()
            self._agent = Agent(
                model=self._model,
                name="llm_service_agent",
                instruction=(
                    "You are a helpful AI assistant specialized in resume analysis "
                    "and job description parsing. Always respond with valid JSON when asked."
                ),
            )
            self._runner = Runner(
                agent=self._agent,
                app_name="job_booster",
                session_service=self._session_service,
            )
            logger.info(f"LLMService initialized with model: {self._model}")
        except ImportError as exc:
            logger.error(f"google-adk is not installed or could not be imported: {exc}")
        except Exception as exc:
            logger.error(f"Failed to initialize ADK LLMService: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate text using the LLM based on a prompt and optional context.

        Args:
            prompt: The text prompt to send to the LLM.
            context: Optional additional context dict merged into the prompt.

        Returns:
            The generated text string, or an empty string on error.
        """
        if not self._runner:
            logger.warning("LLMService is in mock mode. Returning empty string.")
            return ""

        try:
            from google.genai import types as genai_types

            full_prompt = prompt
            if context:
                context_str = json.dumps(context, indent=2, default=str)
                full_prompt = f"{prompt}\n\nContext:\n{context_str}"

            import asyncio
            import uuid

            session_id = str(uuid.uuid4())
            user_id = "llm_service_user"

            # Create session and run
            self._session_service.create_session(
                app_name="job_booster",
                user_id=user_id,
                session_id=session_id,
            )

            content = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=full_prompt)],
            )

            final_response = ""
            for event in self._runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response = event.content.parts[0].text or ""
                    break

            return final_response

        except Exception as exc:
            logger.error(f"LLMService.generate_text error: {exc}")
            return ""

    def generate_json(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a JSON-structured response from the LLM.

        Args:
            prompt: The text prompt. Should instruct the model to return JSON.
            context: Optional additional context.

        Returns:
            Parsed JSON dictionary, or empty dict on error.
        """
        json_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Respond ONLY with a valid JSON object. "
            "Do not include any text before or after the JSON."
        )
        raw = self.generate_text(json_prompt, context)
        if not raw:
            return {}

        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = [l for l in lines[1:] if l.strip() != "```"]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(f"LLMService.generate_json JSON parse error: {exc}\nRaw response: {raw[:500]}")
            return {}

    def call_llm_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a specific named operation via the LLM (prompt-based tool simulation).

        Args:
            tool_name: Name of the logical tool/operation.
            tool_input: Input parameters for the tool.

        Returns:
            Tool output as a dictionary.
        """
        prompt = (
            f"Execute the following tool: {tool_name}\n"
            f"Input: {json.dumps(tool_input, indent=2, default=str)}\n\n"
            "Return the result as a JSON object."
        )
        result = self.generate_json(prompt)
        logger.info(f"LLMService.call_llm_tool '{tool_name}' executed.")
        return result
