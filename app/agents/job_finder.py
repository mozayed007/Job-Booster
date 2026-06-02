"""Job Finder Agent — finds AI/ML job listings matching user profile."""

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.web_tools import fetch_tool, search_tool
from app.pipelines.state import PipelineState


class JobListing(BaseModel):
    """A single job listing."""

    title: str
    company: str
    location: str = ""
    url: str = ""
    match_score: float = 0.0
    match_reasons: list[str] = Field(default_factory=list)
    visa_status: str = "Unknown"
    salary: str = ""


class JobFinderOutput(BaseModel):
    """Output from the job finder."""

    search_queries: list[str] = Field(default_factory=list)
    listings: list[JobListing] = Field(default_factory=list)
    summary: str = ""


class JobFinderAgent(BaseAgent):
    """Finds AI/ML job listings matching the user's profile."""

    output_type = JobFinderOutput
    tools = [search_tool, fetch_tool]

    async def execute(self, state: PipelineState) -> None:
        """Pipeline integration: search for jobs and store in artifacts."""
        result = await self.search(state.get_resume_text())
        state.artifacts["job_finder"] = result

    async def search(
        self,
        resume_text: str,
        top_skills: list[str] | None = None,
        target_roles: list[str] | None = None,
        location_preference: str = "remote",
        seniority_level: str | None = None,
        visa_required: bool = False,
        max_results: int = 15,
    ) -> JobFinderOutput:
        """Search for job listings matching the user's profile.

        Args:
            resume_text: The user's resume text
            top_skills: Optional list of top skills to emphasize
            target_roles: Optional list of target role titles
            location_preference: Location preference (remote, hybrid, specific city)
            seniority_level: Seniority level (junior, mid, senior, etc.)
            visa_required: Whether visa sponsorship is required
            max_results: Maximum number of results to return

        Returns:
            JobFinderOutput with search queries, listings, and summary
        """
        if not self._agent:
            return JobFinderOutput(
                search_queries=[],
                listings=[],
                summary="Error: Job finder agent not available.",
            )

        prompt = self._build_prompt(
            resume_text,
            top_skills,
            target_roles,
            location_preference,
            seniority_level,
            visa_required,
            max_results,
        )

        try:
            result = await self._agent.run(prompt)
            return result.output
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return JobFinderOutput(
                search_queries=[],
                listings=[],
                summary=f"Error searching for jobs: {e}",
            )

    def _build_prompt(
        self,
        resume_text: str,
        top_skills: list[str] | None,
        target_roles: list[str] | None,
        location_preference: str,
        seniority_level: str | None,
        visa_required: bool,
        max_results: int,
    ) -> str:
        """Build the user prompt for job searching."""
        parts = [
            "Find AI/ML job listings matching the following profile.",
            "",
            "## Resume",
            resume_text[:5000],
            "",
            "## Search Criteria",
            f"- Location: {location_preference}",
        ]

        if top_skills:
            parts.append(f"- Top Skills: {', '.join(top_skills)}")
        if target_roles:
            parts.append(f"- Target Roles: {', '.join(target_roles)}")
        if seniority_level:
            parts.append(f"- Seniority: {seniority_level}")
        if visa_required:
            parts.append("- Visa Sponsorship: Required")

        parts.extend(
            [
                f"- Max Results: {max_results}",
                "",
                "## Instructions",
                "1. Generate targeted search queries for credible sources",
                "2. Score each listing on skill overlap, role match, location fit",
                "3. Research visa sponsorship status where relevant",
                "4. Provide a summary with recommendations",
            ]
        )

        return "\n".join(parts)


async def find_jobs(
    resume_text: str,
    top_skills: list[str] | None = None,
    target_roles: list[str] | None = None,
    location_preference: str = "remote",
    seniority_level: str | None = None,
    visa_required: bool = False,
    max_results: int = 15,
) -> JobFinderOutput:
    """Convenience function: search for jobs matching a profile.

    Args:
        resume_text: The user's resume text
        top_skills: Optional list of top skills
        target_roles: Optional list of target roles
        location_preference: Location preference
        seniority_level: Seniority level
        visa_required: Whether visa sponsorship is required
        max_results: Maximum results to return

    Returns:
        JobFinderOutput with search queries, listings, and summary
    """
    from app.agents.base_agent import get_agent

    agent = get_agent("job_finder")
    if agent is None:
        return JobFinderOutput(
            search_queries=[],
            listings=[],
            summary="Error: Job finder agent not available.",
        )

    return await agent.search(
        resume_text,
        top_skills,
        target_roles,
        location_preference,
        seniority_level,
        visa_required,
        max_results,
    )
