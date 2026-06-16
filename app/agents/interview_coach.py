"""Interview Prep Coach — behavioral questions, technical topics, STAR stories, prep tips."""

from typing import cast

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.web_tools import search_tool
from app.pipelines.state import PipelineState


class BehavioralQuestion(BaseModel):
    question: str
    category: str = ""  # e.g., "leadership", "conflict", "failure", "teamwork"
    star_story_prompt: str = ""  # guidance on what Situation-Task-Action-Result to use
    key_points: list[str] = Field(default_factory=list)


class TechnicalTopic(BaseModel):
    area: str  # e.g., "system design", "Python internals", "ML fundamentals"
    likely_question: str
    preparation_tips: list[str] = Field(default_factory=list)


class RoleSpecificQuestion(BaseModel):
    question: str
    context: str = ""  # why this question matters for the specific role
    suggested_approach: str = ""


class STARStory(BaseModel):
    title: str = ""
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    linked_question: str = ""  # which behavioral question this story answers


class InterviewCoachOutput(BaseModel):
    behavioral_questions: list[BehavioralQuestion] = Field(default_factory=list)
    technical_topics: list[TechnicalTopic] = Field(default_factory=list)
    role_specific_questions: list[RoleSpecificQuestion] = Field(default_factory=list)
    star_stories: list[STARStory] = Field(default_factory=list)
    preparation_tips: list[str] = Field(default_factory=list)


class InterviewCoachAgent(BaseAgent):
    """Generates interview prep material from resume and job description."""

    output_type = InterviewCoachOutput
    tools = [search_tool]

    async def execute(self, state: PipelineState) -> None:
        result = await self.coach(
            state.get_resume_text(),
            state.job_text if state.job_text else None,
            role_type=state.inputs.get("role_type"),
        )
        state.artifacts["interview_coach"] = result

    async def coach(
        self,
        resume_text: str,
        job_description: str | None = None,
        role_type: str | None = None,
    ) -> InterviewCoachOutput:
        if not self._agent:
            return InterviewCoachOutput(
                preparation_tips=["Error: Interview coach agent not available."],
            )

        prompt = self._build_prompt(resume_text, job_description, role_type)

        try:
            result = await self._agent.run(prompt)
            return cast(InterviewCoachOutput, result.output)
        except Exception as e:
            logger.error(f"Interview coaching failed: {e}")
            return InterviewCoachOutput(
                preparation_tips=[f"Error generating interview prep: {e}"],
            )

    def _build_prompt(
        self,
        resume_text: str,
        job_description: str | None,
        role_type: str | None,
    ) -> str:
        parts = [
            "Prepare interview coaching material based on the candidate's resume and target role.",
            "",
            "## Resume",
            resume_text[:8000],
        ]

        if job_description:
            parts.extend(
                [
                    "",
                    "## Job Description",
                    job_description[:4000],
                ]
            )

        if role_type:
            parts.extend(
                [
                    "",
                    f"Role type: {role_type}",
                ]
            )

        parts.append("""

## Output Sections

1. **Behavioral questions** — 6-8 questions tailored to the candidate and role.
   - Cover categories: leadership, conflict, failure, teamwork, ownership, growth mindset
   - Each question includes a STAR story prompt guiding which experience to draw from

2. **Technical topics** — 3-5 areas likely to be tested, based on the JD and resume.
   - For each: likely question, preparation tips, key concepts to review

3. **Role-specific questions** — 3-4 questions specific to the company/industry.
   - Why this company? Why this team? Domain-specific scenarios

4. **STAR stories** — Extract 4-5 reusable stories from the resume.
   - Map each to a common behavioral question it answers
   - Ensure each has a clear metric or outcome in the Result

5. **Preparation tips** — 3-5 actionable tips (company research, question prep, logistics)

## Quality Rules
- Questions must be specific to the candidate's actual experience, not generic
- STAR stories must trace back to resume facts — no fabrication
- Technical topics should reflect the actual tech stack in the JD/resume
- For each behavioral question, provide a distinct story — no reusing the same experience
""")

        return "\n".join(parts)


async def prep_for_interview(
    resume_text: str,
    job_description: str | None = None,
    role_type: str | None = None,
) -> InterviewCoachOutput:
    from app.agents.base_agent import get_agent

    agent = get_agent("interview_coach")
    if agent is None:
        return InterviewCoachOutput(
            preparation_tips=["Error: Interview coach agent not available."],
        )

    return await cast(InterviewCoachAgent, agent).coach(resume_text, job_description, role_type)
