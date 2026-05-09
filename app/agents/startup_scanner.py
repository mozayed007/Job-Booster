"""Startup Scanner Agent - Pydantic AI agent for type-safe job extraction."""

import asyncio
import json
from pathlib import Path
from typing import List, Optional

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

from contextlib import contextmanager

from app.core.llm_config import init_ai_stack
from app.models.startup_model import JobOpening, ScannerState, Startup, UserProfile
from app.services.scraper_service import get_scraper
from app.services.startup_parser import parse_startups_file


@contextmanager
def _trace(name: str, **kwargs):
    if logfire is not None:
        with logfire.span(name, **kwargs):
            yield
    else:
        yield


# System prompt for job extraction
JOB_EXTRACTION_PROMPT = """You are a job extraction assistant. Extract job openings from career page content.

Focus on roles matching these skills (score higher for matches):
- AI/ML, Deep Learning, Machine Learning
- GPU/CUDA optimization, Distributed Systems
- Research, MLOps, Data Science
- Python, PyTorch, TensorFlow
- MoE (Mixture of Experts), Multimodal AI
- NLP, Computer Vision, EEG/BCI

For each job found, extract:
1. title: The job title
2. location: Job location (default "Remote" if not specified)
3. requirements: Key skills/requirements as a list
4. link: URL or "N/A" if not available
5. relevance_score: 0.0-1.0 based on skill match

Only return jobs that seem relevant to AI/ML/Tech. Skip non-technical roles.
If no relevant jobs found, return an empty list."""


class StartupScannerAgent:
    """
    Agent that scans startup career pages and extracts relevant job openings.

    Uses:
    - Pydantic AI for type-safe structured extraction
    - Crawl4AI for career page scraping
    - LiteLLM for multi-provider LLM support (including Ollama)
    - Logfire for observability
    """

    def __init__(
        self,
        user_profile: Optional[UserProfile] = None,
        state_file: Optional[Path] = None,
    ):
        self.user_profile = user_profile or UserProfile()
        self.state_file = state_file or Path("scanner_state.json")
        self.scraper = get_scraper()
        self.state = self._load_state()

        # Initialize AI stack
        init_ai_stack()

        # Create Pydantic AI agent for job extraction
        # For Gemini: use google-gla:model format directly
        # For Ollama/OpenAI: could use LiteLLMProvider with a proxy
        if PYDANTIC_AI_AVAILABLE:
            from app.core.model_registry import create_agent

            self.job_extractor = create_agent(
                output_type=list[JobOpening],
                system_prompt=JOB_EXTRACTION_PROMPT,
            )
            logger.info("Initialized job extractor via ModelRegistry")
        else:
            self.job_extractor = None

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

    async def extract_jobs(self, startup_name: str, career_content: str) -> List[JobOpening]:
        """
        Extract jobs from career page content using Pydantic AI.

        Args:
            startup_name: Name of the startup
            career_content: Markdown content of career page

        Returns:
            List of extracted JobOpening objects (guaranteed valid structure)
        """
        if not self.job_extractor:
            logger.error("Pydantic AI not available")
            return []

        if not career_content or len(career_content) < 50:
            return []

        with _trace("extract_jobs", startup=startup_name):
            try:
                # Truncate very long content
                content = career_content[:10000] if len(career_content) > 10000 else career_content

                prompt = f"Startup: {startup_name}\n\nCareer Page Content:\n{content}"

                # Pydantic AI guarantees valid list[JobOpening] output
                result = await self.job_extractor.run(prompt)

                # Add startup name to each job
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

    async def scan_startup(self, startup: Startup) -> List[JobOpening]:
        """
        Scan a single startup for job openings.

        Args:
            startup: Startup to scan

        Returns:
            List of found job openings
        """
        if not startup.website:
            return []

        with _trace("scan_startup", name=startup.name, city=startup.city):
            # Scrape career page
            content = await self.scraper.scrape_careers(startup.website)

            if not content:
                logger.debug(f"No career page found for {startup.name}")
                return []

            # Extract jobs
            jobs = await self.extract_jobs(startup.name, content)

            # Mark as processed
            self.state.add_processed(startup.name)

            return jobs

    async def process_batch(
        self,
        batch_size: int = 10,
        startups: Optional[List[Startup]] = None,
    ) -> List[JobOpening]:
        """
        Process a batch of startups.

        Args:
            batch_size: Number of startups to process
            startups: Optional list of startups (loads from file if not provided)

        Returns:
            List of found job openings in this batch
        """
        if startups is None:
            all_startups = parse_startups_file()
            # Filter to those with websites, not yet processed
            startups = [
                s for s in all_startups if s.website and s.name not in self.state.processed_startups
            ]

        # Take batch
        batch = startups[:batch_size]

        if not batch:
            self.state.status = "complete"
            self._save_state()
            return []

        with _trace("process_batch", batch_size=len(batch), batch_number=self.state.batch_number):
            all_jobs: List[JobOpening] = []

            for startup in batch:
                jobs = await self.scan_startup(startup)
                all_jobs.extend(jobs)

            # Update state
            self.state.batch_number += 1
            self.state.add_roles(all_jobs)
            self._save_state()

            if logfire:
                logfire.info(
                    "batch_complete",
                    batch_number=self.state.batch_number,
                    startups_scanned=len(batch),
                    jobs_found=len(all_jobs),
                    total_promising=len(self.state.promising_roles),
                )

            return all_jobs

    def get_top_roles(self, limit: int = 20) -> List[JobOpening]:
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


# Convenience functions
async def quick_scan(batch_size: int = 5) -> List[JobOpening]:
    """Quick scan of a small batch for testing."""
    agent = StartupScannerAgent()
    return await agent.process_batch(batch_size=batch_size)


if __name__ == "__main__":
    # Quick test
    async def test():
        agent = StartupScannerAgent()
        print("Progress:", agent.get_progress())

        # Scan a small batch
        jobs = await agent.process_batch(batch_size=3)
        print(f"Found {len(jobs)} jobs")

        for job in jobs[:5]:
            print(f"  - {job.title} at {job.startup_name} ({job.relevance_score:.2f})")

    asyncio.run(test())
