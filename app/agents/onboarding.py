"""Onboarding Agent — collects personal context via conversational interview."""

from typing import cast

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.core.model_registry import create_agent
from app.pipelines.state import PipelineState

# Marker the agent emits when it has gathered enough context.
PROFILE_READY_MARKER = "[PROFILE_READY]"


class PersonalProfileOutput(BaseModel):
    """Structured personal context gathered during onboarding.

    This data is STRICTLY isolated to the gap-recommendation agent. It must
    never be injected into resume tailoring, cover letter generation, or CV
    extraction — those agents must never read personal context to avoid
    fabricating resume bullets that do not reflect the user's real experience.
    """

    hobbies: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    free_time_activities: list[str] = Field(default_factory=list)
    favorite_tech_or_domains: list[str] = Field(default_factory=list)
    work_style: str = ""
    short_bio: str = ""
    raw_transcript: str = ""


class OnboardingAgent(BaseAgent):
    """Conversational onboarding agent that gathers personal context.

    Operates in two modes:
    - chat_turn(): free-text multi-turn interview using a plain (no output_type)
      pydantic-ai agent. Returns the next question or [PROFILE_READY].
    - finalize(): single structured-output call producing PersonalProfileOutput
      from the full transcript.
    """

    output_type = PersonalProfileOutput

    def __init__(self, config, base_dir) -> None:
        super().__init__(config, base_dir)
        # A separate plain agent (no output_type) for free-text chat turns.
        try:
            self._chat_agent = create_agent(
                output_type=None,
                system_prompt=self.system_prompt,
                retries=self.config.model_retries,
                name=f"{self.config.name} (chat)",
                description=self.config.description,
            )
        except Exception as e:
            logger.error(f"Failed to build chat agent for onboarding: {e}")
            self._chat_agent = None

    async def execute(self, state: PipelineState) -> None:
        """Pipeline integration: finalize profile from a stored transcript.

        Expects state.inputs["onboarding_history"] to be a list of {"role","content"}
        dicts from the conversation. Produces a PersonalProfileOutput artifact.
        """
        history = state.inputs.get("onboarding_history", [])
        if not history:
            state.errors.append("Onboarding agent: no onboarding_history in state.inputs")
            return
        result = await self.finalize(history)
        state.artifacts["onboarding_agent"] = result

    async def chat_turn(self, user_msg: str, history: list[dict] | None = None) -> str:
        """Return the agent's next question or [PROFILE_READY].

        Args:
            user_msg: The user's latest message.
            history: Prior conversation as a list of {"role","content"} dicts.
                role is "user" or "assistant".

        Returns:
            The assistant's next message. May contain [PROFILE_READY].
        """
        if not self._chat_agent:
            return "Error: Onboarding chat agent not available."

        transcript = self._format_transcript(history or [])
        prompt = self._build_chat_prompt(transcript, user_msg)

        try:
            result = await self._chat_agent.run(prompt)
            output = getattr(result, "output", result)
            return str(output)
        except Exception as e:
            logger.error(f"Onboarding chat turn failed: {e}")
            return f"Sorry, I had trouble responding. (Error: {e})"

    async def finalize(self, history: list[dict]) -> PersonalProfileOutput:
        """Convert a conversation transcript into a structured profile.

        Args:
            history: Full conversation as [{"role","content"}] dicts.

        Returns:
            PersonalProfileOutput populated from the conversation.
        """
        transcript = self._format_transcript(history)
        if not transcript.strip():
            return PersonalProfileOutput()

        if not self._agent:
            return PersonalProfileOutput()

        prompt = (
            "FINALIZE: Convert this onboarding conversation into a "
            f"structured profile.\n\n{transcript}"
        )

        try:
            result = await self._agent.run(prompt)
            return cast(PersonalProfileOutput, result.output)
        except Exception as e:
            logger.error(f"Onboarding finalize failed: {e}")
            return PersonalProfileOutput(raw_transcript=transcript)

    @staticmethod
    def _format_transcript(history: list[dict]) -> str:
        """Format conversation history into a readable transcript."""
        lines: list[str] = []
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            label = "User" if role == "user" else "Assistant"
            lines.append(f"{label}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _build_chat_prompt(transcript: str, user_msg: str) -> str:
        """Build the prompt for a chat turn."""
        parts = ["CHAT: You are mid-conversation with the user."]
        if transcript:
            parts.append("")
            parts.append("Conversation so far:")
            parts.append(transcript)
        parts.append("")
        parts.append(f"User's latest message: {user_msg}")
        parts.append("")
        parts.append(
            "Respond with your next question (1-3 sentences), or emit "
            f"{PROFILE_READY_MARKER} on its own line if you have enough across "
            "at least 3 of the 5 areas (hobbies, interests, free-time, "
            "favorite tech/domains, work style)."
        )
        return "\n".join(parts)


async def chat_turn(user_msg: str, history: list[dict] | None = None) -> str:
    """Convenience: single chat turn for the onboarding interview."""
    from app.agents.base_agent import get_agent

    agent = get_agent("onboarding_agent")
    if agent is None:
        return "Error: Onboarding agent not available."
    return await cast(OnboardingAgent, agent).chat_turn(user_msg, history)


async def finalize_onboarding(history: list[dict]) -> PersonalProfileOutput:
    """Convenience: finalize the onboarding conversation into a structured profile."""
    from app.agents.base_agent import get_agent

    agent = get_agent("onboarding_agent")
    if agent is None:
        return PersonalProfileOutput()
    return await cast(OnboardingAgent, agent).finalize(history)
