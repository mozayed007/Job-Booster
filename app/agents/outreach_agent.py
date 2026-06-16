"""Post-Application Outreach Agent — follow-ups, thank-you notes, cold outreach."""

from typing import cast

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.web_tools import search_tool
from app.pipelines.state import PipelineState


class FollowUpEmail(BaseModel):
    subject: str
    body: str


class ThankYouEmail(BaseModel):
    subject: str
    body: str


class ColdOutreachMessage(BaseModel):
    platform: str = "LinkedIn"
    subject: str = ""
    body: str


class ReferralRequest(BaseModel):
    subject: str
    body: str


class OutreachOutput(BaseModel):
    follow_up_email: FollowUpEmail | None = None
    thank_you_email: ThankYouEmail | None = None
    cold_outreach_message: ColdOutreachMessage | None = None
    referral_request: ReferralRequest | None = None
    sending_tips: list[str] = Field(default_factory=list)


class OutreachAgent(BaseAgent):
    """Generates post-application outreach messages: follow-ups, thank-yous, cold outreach."""

    output_type = OutreachOutput
    tools = [search_tool]

    async def execute(self, state: PipelineState) -> None:
        result = await self.generate(
            state.get_resume_text(),
            state.job_text,
            company_name=state.inputs.get("company_name"),
            hiring_manager=state.inputs.get("hiring_manager"),
            days_since_application=state.inputs.get("days_since_application"),
            interview_stage=state.inputs.get("interview_stage"),
        )
        state.artifacts["outreach_agent"] = result

    async def generate(
        self,
        resume_text: str,
        job_text: str,
        company_name: str | None = None,
        hiring_manager: str | None = None,
        days_since_application: int | None = None,
        interview_stage: str | None = None,
    ) -> OutreachOutput:
        if not self._agent:
            return OutreachOutput(
                sending_tips=["Error: Outreach agent not available."],
            )

        prompt = self._build_prompt(
            resume_text,
            job_text,
            company_name,
            hiring_manager,
            days_since_application,
            interview_stage,
        )

        try:
            result = await self._agent.run(prompt)
            return cast(OutreachOutput, result.output)
        except Exception as e:
            logger.error(f"Outreach generation failed: {e}")
            return OutreachOutput(
                sending_tips=[f"Error generating outreach messages: {e}"],
            )

    def _build_prompt(
        self,
        resume_text: str,
        job_text: str,
        company_name: str | None,
        hiring_manager: str | None,
        days_since_application: int | None,
        interview_stage: str | None,
    ) -> str:
        parts = [
            "Generate outreach messages for a job applicant. Produce all applicable messages.",
            "",
            "## Resume",
            resume_text[:6000],
            "",
            "## Job Description",
            job_text[:4000],
        ]

        if company_name:
            parts.append(f"\nCompany: {company_name}")
        if hiring_manager:
            parts.append(f"Hiring Manager: {hiring_manager}")
        if days_since_application is not None:
            parts.append(f"Days since application: {days_since_application}")
        if interview_stage:
            parts.append(f"Current interview stage: {interview_stage}")

        parts.append("""

## Message Types

1. **Follow-up email** — Send if applied 7+ days ago with no response.
   - Polite, concise, reiterates interest
   - References the specific role and application date
   - Optionally adds a brief new data point (recent achievement, relevant project)

2. **Thank-you email** — Send within 24 hours after any interview.
   - References a specific topic discussed
   - Reinforces enthusiasm for the role/team
   - Brief and genuine — not a repetition of the cover letter

3. **Cold outreach message** — Send to hiring manager or team lead before applying.
   - Expresses specific interest in their work (reference a project, post, or product)
   - States the role being pursued concisely
   - Ends with a soft ask (quick chat, informational interview)

4. **Referral request** — Send to an existing connection at the company.
   - Polite, low-pressure
   - Explains why the role fits (briefly)
   - Makes it easy for them to refer (link to JD, deadline)
""")

        return "\n".join(parts)


async def generate_outreach(
    resume_text: str,
    job_text: str,
    company_name: str | None = None,
    hiring_manager: str | None = None,
    days_since_application: int | None = None,
    interview_stage: str | None = None,
) -> OutreachOutput:
    from app.agents.base_agent import get_agent

    agent = get_agent("outreach_agent")
    if agent is None:
        return OutreachOutput(
            sending_tips=["Error: Outreach agent not available."],
        )

    return await cast(OutreachAgent, agent).generate(
        resume_text,
        job_text,
        company_name,
        hiring_manager,
        days_since_application,
        interview_stage,
    )
