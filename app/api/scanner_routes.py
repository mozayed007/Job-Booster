"""FastAPI Router for Startup Scanner endpoints."""

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel

from app.agents.startup_scanner import StartupScannerAgent
from app.models.startup_model import JobOpening, Startup
from app.services.startup_parser import get_startups_by_city, parse_startups_file

router = APIRouter(prefix="/scanner", tags=["Startup Scanner"])


# Response Models
class ScanProgressResponse(BaseModel):
    total_startups: int
    with_websites: int
    processed: int
    remaining: int
    batch_number: int
    promising_roles: int
    status: str


class ScanBatchResponse(BaseModel):
    jobs_found: int
    jobs: list[JobOpening]
    progress: ScanProgressResponse


class StartupsListResponse(BaseModel):
    total: int
    cities: list[str]
    startups: list[Startup]


# Global agent instance (lazy loaded)
_agent: StartupScannerAgent | None = None


def get_agent() -> StartupScannerAgent:
    """Get the scanner agent from the registry."""
    global _agent
    if _agent is None:
        from app.agents.base_agent import get_agent as _base_get_agent

        agent = _base_get_agent("startup_scanner")
        if agent is None:
            raise RuntimeError("startup_scanner agent not found — check agents.yaml")
        if not isinstance(agent, StartupScannerAgent):
            raise RuntimeError(f"Expected StartupScannerAgent, got {type(agent).__name__}")
        _agent = agent
    return _agent


# Background task for scanning
async def _scan_batch_task(batch_size: int) -> None:
    """Background task to scan a batch."""
    agent = get_agent()
    await agent.process_batch(batch_size=batch_size)


# Endpoints
@router.get("/startups", response_model=StartupsListResponse)
async def list_startups(
    city: str | None = Query(None, description="Filter by city"),
    category: str | None = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all available startups from the database."""
    startups = parse_startups_file()

    # Apply filters
    if city:
        startups = [s for s in startups if s.city.lower() == city.lower()]
    if category:
        startups = [s for s in startups if s.category.lower() == category.lower()]

    # Get unique cities
    cities = sorted(set(s.city for s in startups))

    # Paginate
    total = len(startups)
    startups = startups[offset : offset + limit]

    return StartupsListResponse(
        total=total,
        cities=cities,
        startups=startups,
    )


@router.get("/progress", response_model=ScanProgressResponse)
async def get_progress():
    """Get current scanning progress."""
    agent = get_agent()
    progress = agent.get_progress()
    return ScanProgressResponse(**progress)


@router.post("/scan/batch", response_model=ScanBatchResponse)
async def scan_batch(
    batch_size: int = Query(10, ge=1, le=50, description="Number of startups to scan"),
):
    """
    Scan a batch of startups for job openings.

    This processes startups sequentially and returns found jobs.
    """
    agent = get_agent()

    jobs = await agent.process_batch(batch_size=batch_size)
    progress = agent.get_progress()

    return ScanBatchResponse(
        jobs_found=len(jobs),
        jobs=jobs,
        progress=ScanProgressResponse(**progress),
    )


@router.post("/scan/background")
async def scan_batch_background(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(10, ge=1, le=50),
):
    """
    Start a background scan task.

    Returns immediately while scanning continues in background.
    Check /progress endpoint for status.
    """
    background_tasks.add_task(_scan_batch_task, batch_size)

    return {
        "status": "started",
        "message": f"Scanning {batch_size} startups in background",
    }


@router.get("/jobs/top", response_model=list[JobOpening])
async def get_top_jobs(
    limit: int = Query(20, ge=1, le=100, description="Number of jobs to return"),
    city: str | None = Query(None, description="Filter by startup city"),
):
    """Get top job openings ranked by relevance score."""
    agent = get_agent()
    return agent.get_top_roles(limit=limit, city=city)


@router.post("/reset")
async def reset_scanner():
    """Reset scanner state to start fresh."""
    global _agent
    _agent = None

    # Delete state file if exists
    from pathlib import Path

    state_file = Path("scanner_state.json")
    if state_file.exists():
        state_file.unlink()

    return {"status": "reset", "message": "Scanner state cleared"}


@router.get("/cities")
async def list_cities():
    """Get list of all cities with startup counts."""
    startups = parse_startups_file()
    by_city = get_startups_by_city(startups)

    return {city: len(items) for city, items in sorted(by_city.items(), key=lambda x: -len(x[1]))}
