"""Job Finder Agent — finds job listings matching the user's resume and preferences."""

from typing import cast

from loguru import logger
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.discovery_tools import (
    list_imported_startups_tool_wrapped,
    search_imported_jobs_tool_wrapped,
)
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
    """Finds job listings matching the user's resume and preferences."""

    output_type = JobFinderOutput
    tools = [
        search_tool,
        fetch_tool,
        search_imported_jobs_tool_wrapped,
        list_imported_startups_tool_wrapped,
    ]

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

        seed_companies = self._load_seed_companies(
            top_skills=top_skills,
            target_roles=target_roles,
        )
        imported_jobs = await self._load_ranked_imported_jobs(
            top_skills=top_skills,
            target_roles=target_roles,
        )
        prompt = self._build_prompt(
            resume_text,
            top_skills,
            target_roles,
            location_preference,
            seniority_level,
            visa_required,
            max_results,
            seed_companies=seed_companies,
            imported_jobs=imported_jobs,
        )

        try:
            result = await self._agent.run(prompt)
            return cast(JobFinderOutput, result.output)
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return JobFinderOutput(
                search_queries=[],
                listings=[],
                summary=f"Error searching for jobs: {e}",
            )

    def _load_seed_companies(
        self,
        limit: int = 10,
        top_skills: list[str] | None = None,
        target_roles: list[str] | None = None,
    ) -> list[str]:
        """Companies imported from BigSet, ranked by resume/profile overlap."""
        try:
            from app.services.bigset_import_service import get_seed_companies
            from app.services.db_service import get_db_session
            from app.services.user_profile_service import load_user_profile

            profile = load_user_profile()
            skills = list(top_skills or profile.skills)
            roles = list(target_roles or profile.target_role_keywords)

            db = get_db_session()
            try:
                return get_seed_companies(
                    db,
                    limit=limit,
                    skills=skills,
                    role_keywords=roles,
                )
            finally:
                db.close()
        except Exception as e:
            logger.debug("BigSet seed companies unavailable: {}", e)
            return []

    async def _load_ranked_imported_jobs(
        self,
        limit: int = 8,
        top_skills: list[str] | None = None,
        target_roles: list[str] | None = None,
    ) -> list[dict]:
        """Top imported postings by profile fit for prompt context."""
        try:
            from app.services.db_service import get_db_session
            from app.services.discovery_query_service import search_imported_jobs
            from app.services.job_fit_service import rank_imported_jobs
            from app.services.user_profile_service import load_user_profile

            profile = load_user_profile()
            if not profile.bigset.enabled or not profile.bigset.prefer_imported_jobs:
                return []

            query = " ".join(
                k
                for k in (top_skills or profile.skills)[:5]
                + (target_roles or profile.target_role_keywords)[:3]
                if k
            )
            if query.strip():
                return await search_imported_jobs(query, profile, limit=limit)
            db = get_db_session()
            try:
                return rank_imported_jobs(db, profile, limit=limit)
            finally:
                db.close()
        except Exception as e:
            logger.debug("Ranked imported jobs unavailable: {}", e)
            return []

    def _build_prompt(
        self,
        resume_text: str,
        top_skills: list[str] | None,
        target_roles: list[str] | None,
        location_preference: str,
        seniority_level: str | None,
        visa_required: bool,
        max_results: int,
        seed_companies: list[str] | None = None,
        imported_jobs: list[dict] | None = None,
    ) -> str:
        """Build the user prompt for job searching."""
        parts = [
            "Find job listings matching the following candidate profile.",
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
        if seed_companies:
            parts.append(
                "- Prioritize openings at these employers from imported datasets: "
                f"{', '.join(seed_companies)}"
            )
        if imported_jobs:
            parts.append("")
            parts.append("## Imported corpus (check before web search)")
            for j in imported_jobs[:8]:
                parts.append(
                    f"- [{j.get('fit_score', j.get('combined_score', '?'))}] "
                    f"{j.get('title')} @ {j.get('company')} "
                    f"({j.get('location', '')}) — {j.get('snippet', '')[:120]}"
                )
            parts.append("- Use tool search_imported_jobs for deeper queries on this corpus.")

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

    return await cast(JobFinderAgent, agent).search(
        resume_text,
        top_skills,
        target_roles,
        location_preference,
        seniority_level,
        visa_required,
        max_results,
    )
