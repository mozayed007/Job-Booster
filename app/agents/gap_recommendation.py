"""Gap Recommendation Agent — enjoyable project/course recs that cover skill gaps."""

from typing import Any, cast

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.pipelines.state import PipelineState


class Recommendation(BaseModel):
    """One enjoyable project/course suggestion targeting a specific skill gap."""

    target_gap: str
    project_title: str
    project_description: str
    why_enjoyable: str
    estimated_effort: str = ""
    learning_resources: list[str] = Field(default_factory=list)
    type: str = "project"


class GapRecommendationOutput(BaseModel):
    """Output from the gap-recommendation agent.

    Recommendations are learning/build material only — never resume content.
    Personal context (hobbies, interests) is used solely to make recs enjoyable
    and is NEVER injected into resume generation.
    """

    recommendations: list[Recommendation] = Field(default_factory=list)
    summary: str = ""
    uncovered_gaps: list[str] = Field(default_factory=list)


class GapRecommendationAgent(BaseAgent):
    """Recommends enjoyable projects/courses that cover technical skill gaps.

    Consumes the canonical gap list from RecommendationService and the user's
    personal context (gathered by the onboarding agent) to produce
    recommendations mapped to the user's real interests.
    """

    output_type = GapRecommendationOutput

    async def execute(self, state: PipelineState) -> None:
        """Pipeline integration: recommend from gaps + personal context in state.

        Expects state.inputs["skill_gaps"] (list[str]) and optionally
        state.inputs["personal_context"] (dict) and state.inputs["job_context"].
        """
        gaps = state.inputs.get("skill_gaps", [])
        if not gaps:
            state.errors.append("Gap recommendation agent: no skill_gaps in state.inputs")
            return
        personal_context = state.inputs.get("personal_context", {})
        job_context = state.inputs.get("job_context", "")
        result = await self.recommend(gaps, personal_context, job_context)
        state.artifacts["gap_recommendation_agent"] = result

    async def recommend(
        self,
        gaps: list[str],
        personal_context: dict[str, Any] | None = None,
        job_context: str = "",
    ) -> GapRecommendationOutput:
        """Generate enjoyable recommendations covering the given skill gaps.

        Args:
            gaps: Technical skills missing from the resume vs. the job posting.
            personal_context: Structured profile from onboarding (hobbies,
                interests, etc.). May be empty — recs fall back to broadly
                engaging suggestions and gaps surface in uncovered_gaps.
            job_context: Optional role title or domain for scope tailoring.

        Returns:
            GapRecommendationOutput with 1-3 recs per gap and any uncovered gaps.
        """
        if not gaps:
            return GapRecommendationOutput(summary="No skill gaps provided — nothing to recommend.")

        if not self._agent:
            return GapRecommendationOutput(
                summary="Error: Gap recommendation agent not available.",
                uncovered_gaps=list(gaps),
            )

        prompt = self._build_prompt(gaps, personal_context or {}, job_context)

        try:
            result = await self._agent.run(prompt)
            output = cast(GapRecommendationOutput, result.output)
            if not output.uncovered_gaps and not output.recommendations:
                # LLM returned nothing useful — surface all gaps as uncovered.
                output.uncovered_gaps = list(gaps)
            return output
        except Exception as e:
            logger.error(f"Gap recommendation failed: {e}")
            return GapRecommendationOutput(
                summary=f"Error generating recommendations: {e}",
                uncovered_gaps=list(gaps),
            )

    @staticmethod
    def _build_prompt(
        gaps: list[str],
        personal_context: dict[str, Any],
        job_context: str,
    ) -> str:
        """Build the user prompt for gap recommendations."""
        import json

        parts = [
            "Generate enjoyable, personalized recommendations that cover the "
            "following technical skill gaps.",
            "",
            "## Skill Gaps",
        ]
        for gap in gaps:
            parts.append(f"- {gap}")

        parts.append("")
        parts.append("## Personal Context")
        if personal_context and any(personal_context.values()):
            parts.append("```json")
            parts.append(json.dumps(personal_context, indent=2, default=str))
            parts.append("```")
        else:
            parts.append(
                "(No personal context provided — user has not completed onboarding. "
                "Produce broadly engaging recs and note the profile was empty.)"
            )

        if job_context:
            parts.append("")
            parts.append(f"## Job Context\n{job_context}")

        parts.append("")
        parts.append(
            f"Provide 1-3 recommendations per gap (fewer per gap when there are "
            f"many gaps — scale by gap count). Map each rec to a specific hobby or "
            f"interest from the personal context. Total gaps: {len(gaps)}."
        )
        return "\n".join(parts)


async def recommend_gaps(
    gaps: list[str],
    personal_context: dict[str, Any] | None = None,
    job_context: str = "",
) -> GapRecommendationOutput:
    """Convenience: generate enjoyable recommendations for skill gaps."""
    from app.agents.base_agent import get_agent

    agent = get_agent("gap_recommendation_agent")
    if agent is None:
        return GapRecommendationOutput(
            summary="Error: Gap recommendation agent not available.",
            uncovered_gaps=list(gaps),
        )
    return await cast(GapRecommendationAgent, agent).recommend(gaps, personal_context, job_context)
