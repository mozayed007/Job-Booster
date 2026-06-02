"""Startup Scanner Agent — scans startup career pages and extracts job openings."""

import asyncio
import json
from contextlib import contextmanager
from pathlib import Path

try:
    import logfire
except ImportError:
    logfire = None

from loguru import logger

try:
    import pydantic_ai  # noqa: F401

    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    logger.warning("Pydantic AI not installed. Run: pip install pydantic-ai")

from app.agents.base_agent import AgentConfig, BaseAgent
from app.core.model_registry import init_ai_stack
from app.models.startup_model import JobOpening, ScannerState, Startup, UserProfile
from app.pipelines.state import PipelineState
from app.services.scraper_service import get_scraper
from app.services.startup_parser import parse_startups_file


@contextmanager
def _trace(name: str, **kwargs):
    if logfire is not None:
        with logfire.span(name, **kwargs):
            yield
    else:
        yield


class StartupScannerAgent(BaseAgent):
    """Scans startup career pages and extracts relevant job openings.

    This agent creates its own internal pydantic-ai agent in __init__
    because it needs output_type=list[JobOpening] which can't be a class attribute.
    """

    _skip_base_agent = True

    def __init__(
        self,
        config: AgentConfig,
        base_dir: Path,
        user_profile: UserProfile | None = None,
        state_file: Path | None = None,
    ):
        super().__init__(config, base_dir)
        self.user_profile = user_profile or UserProfile()
        self.state_file = state_file or Path("scanner_state.json")
        self.scraper = get_scraper()
        self.state = self._load_state()

        init_ai_stack()

        if PYDANTIC_AI_AVAILABLE:
            from app.core.model_registry import create_agent

            self.job_extractor = create_agent(
                output_type=list[JobOpening],
                system_prompt=self.system_prompt,
            )
            logger.info("Initialized job extractor via ModelRegistry")
        else:
            self.job_extractor = None

    async def execute(self, state: PipelineState) -> None:
        """Pipeline integration: scan startups and store in artifacts."""
        result = await self.process_batch()
        state.artifacts["startup_scanner"] = result

    def _load_state(self) -> ScannerState:
        """Load scanner state from file or create new."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return ScannerState.model_validate(data)
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
        return ScannerState()

    def _save_state(self) -> None:
        """Save scanner state to file."""
        self.state_file.write_text(self.state.model_dump_json(indent=2))

    async def extract_jobs(self, startup_name: str, career_content: str) -> list[JobOpening]:
        """Extract jobs from career page content using Pydantic AI."""
        if not self.job_extractor:
            logger.error("Pydantic AI not available")
            return []

        if not career_content or len(career_content) < 50:
            return []

        with _trace("extract_jobs", startup=startup_name):
            try:
                content = career_content[:10000] if len(career_content) > 10000 else career_content
                prompt = f"Startup: {startup_name}\n\nCareer Page Content:\n{content}"

                result = await self.job_extractor.run(prompt)

                jobs = []
                for job in result.output:
                    job.startup_name = startup_name
                    jobs.append(job)

                if logfire:
                    logfire.info(
                        "jobs_extracted",
                        startup=startup_name,
                        count=len(jobs),
                        tokens=result.usage().total_tokens if hasattr(result, "usage") else 0,
                    )

                return jobs

            except Exception as e:
                logger.error(f"Job extraction failed for {startup_name}: {e}")
                if logfire:
                    logfire.error("extraction_failed", startup=startup_name, error=str(e))
                return []

    async def scan_startup(self, startup: Startup) -> list[JobOpening]:
        """Scan a single startup for job openings."""
        if not startup.website:
            return []

        with _trace("scan_startup", name=startup.name, city=startup.city):
            content = await self.scraper.scrape_careers(startup.website)

            if not content:
                logger.debug(f"No career page found for {startup.name}")
                return []

            jobs = await self.extract_jobs(startup.name, content)
            self.state.add_processed(startup.name)

            return jobs

    async def process_batch(
        self,
        batch_size: int = 10,
        startups: list[Startup] | None = None,
    ) -> list[JobOpening]:
        """Process a batch of startups."""
        if startups is None:
            all_startups = parse_startups_file()
            startups = [
                s for s in all_startups if s.website and s.name not in self.state.processed_startups
            ]

        batch = startups[:batch_size]

        if not batch:
            self.state.status = "complete"
            self._save_state()
            return []

        with _trace("process_batch", batch_size=len(batch), batch_number=self.state.batch_number):
            all_jobs: list[JobOpening] = []

            for startup in batch:
                jobs = await self.scan_startup(startup)
                all_jobs.extend(jobs)

            self.state.batch_number += 1
            self.state.add_roles(all_jobs)
            self._save_state()

            await self._persist_jobs(all_jobs)

            if logfire:
                logfire.info(
                    "batch_complete",
                    batch_number=self.state.batch_number,
                    startups_scanned=len(batch),
                    jobs_found=len(all_jobs),
                    total_promising=len(self.state.promising_roles),
                )

            return all_jobs

    async def _persist_jobs(self, jobs: list[JobOpening]) -> None:
        """Store extracted jobs in DB and index to vector store."""
        if not jobs:
            return

        from app.services.db_service import DatabaseService, get_db_session
        from app.services.search_service import SearchService
        from app.services.vector_store import get_vector_store

        db = get_db_session()
        try:
            db_svc = DatabaseService(db)
            job_dicts = [
                {
                    "title": j.title,
                    "company": j.startup_name,
                    "location": j.location,
                    "raw_text": (
                        f"{j.title} at {j.startup_name}. Requirements: {', '.join(j.requirements)}"
                    ),
                    "source_url": j.link if j.link != "N/A" else None,
                }
                for j in jobs
            ]
            inserted_ids = db_svc.store_scraped_jobs_batch(job_dicts)

            try:
                vs = get_vector_store()
                if vs.is_available and inserted_ids:
                    search_svc = SearchService(vector_store=vs)
                    for job_opening, job_id in zip(jobs, inserted_ids):
                        text = (
                            f"{job_opening.title} {job_opening.startup_name} "
                            f"{' '.join(job_opening.requirements)}"
                        )
                        await search_svc.index_job(
                            job_id,
                            text,
                            metadata={
                                "startup_name": job_opening.startup_name,
                                "relevance_score": job_opening.relevance_score,
                            },
                        )
            except Exception as idx_err:
                logger.warning(f"Vector indexing failed (non-fatal): {idx_err}")

        except Exception as e:
            logger.error(f"Failed to persist jobs: {e}")
        finally:
            db.close()

    def get_top_roles(self, limit: int = 20) -> list[JobOpening]:
        """Get top roles by relevance score."""
        return self.state.promising_roles[:limit]

    def get_progress(self) -> dict:
        """Get current scanning progress."""
        all_startups = parse_startups_file()
        with_websites = [s for s in all_startups if s.website]

        return {
            "total_startups": len(all_startups),
            "with_websites": len(with_websites),
            "processed": len(self.state.processed_startups),
            "remaining": len(with_websites) - len(self.state.processed_startups),
            "batch_number": self.state.batch_number,
            "promising_roles": len(self.state.promising_roles),
            "status": self.state.status,
        }


async def quick_scan(batch_size: int = 5) -> list[JobOpening]:
    """Convenience function: quick scan of a small batch."""
    from app.agents.base_agent import get_agent

    agent = get_agent("startup_scanner")
    if agent is None:
        logger.error("Startup scanner agent not available")
        return []

    return await agent.process_batch(batch_size=batch_size)


if __name__ == "__main__":

    async def test():
        from app.agents.base_agent import get_agent, load_agents

        load_agents()
        agent = get_agent("startup_scanner")
        if agent is None:
            print("Error: startup_scanner agent not available")
            return

        print("Progress:", agent.get_progress())

        jobs = await agent.process_batch(batch_size=3)
        print(f"Found {len(jobs)} jobs")

        for job in jobs[:5]:
            print(f"  - {job.title} at {job.startup_name} ({job.relevance_score:.2f})")

    asyncio.run(test())
