"""Job discovery endpoints — search across multiple job boards."""


from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from app.services.db_service import (
    DatabaseService,
    get_db_session,
)
from app.services.job_board_scraper import (
    get_available_sources,
    search_all_sources,
)
from app.services.search_service import SearchService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/discovery", tags=["Job Discovery"])


class DiscoverySearchRequest(BaseModel):
    query: str
    location: str = ""
    limit: int = Field(default=20, ge=1, le=100)
    sources: list[str] | None = None


class IndexJobsRequest(BaseModel):
    jobs: list[dict]


@router.post("/search")
async def discovery_search(request: DiscoverySearchRequest):
    """Search across multiple job boards."""
    try:
        results = await search_all_sources(
            query=request.query,
            location=request.location,
            limit=request.limit,
            sources=request.sources,
        )
        total = sum(len(v) for v in results.values())
        # Serialize ScrapedJob objects
        serialized = {}
        for source, jobs in results.items():
            serialized[source] = [j.model_dump() for j in jobs]
        return {
            "success": True,
            "total": total,
            "by_source": {k: len(v) for k, v in results.items()},
            "results": serialized,
        }
    except Exception as e:
        logger.error(f"Discovery search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def list_sources():
    """List available job board sources and their status."""
    sources = get_available_sources()
    return {"success": True, "sources": sources}


@router.post("/index")
async def index_discovered_jobs(request: IndexJobsRequest):
    """Index discovered jobs into the DB and vector store."""
    db = get_db_session()
    try:
        db_svc = DatabaseService(db)

        job_dicts = []
        for job in request.jobs:
            job_dicts.append({
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "raw_text": (
                    f"{job.get('title', '')} at {job.get('company', '')}. "
                    f"{job.get('description', '')}"
                ),
                "source_url": job.get("url", ""),
            })

        inserted_ids = db_svc.store_scraped_jobs_batch(job_dicts)

        # Index to vector store
        indexed = 0
        try:
            vs = get_vector_store()
            if vs.is_available and inserted_ids:
                search_svc = SearchService(vector_store=vs)
                for job_data, job_id in zip(job_dicts, inserted_ids):
                    await search_svc.index_job(job_id, job_data["raw_text"][:5000])
                    indexed += 1
        except Exception as e:
            logger.warning(f"Vector indexing for discovered jobs failed: {e}")

        return {
            "success": True,
            "stored": len(inserted_ids),
            "indexed": indexed,
            "ids": inserted_ids,
        }
    except Exception as e:
        logger.error(f"Index discovered jobs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
