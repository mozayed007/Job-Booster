"""Job discovery endpoints — search across multiple job boards."""


from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.middleware.auth_middleware import get_current_user_dependency
from app.models.db_models import User
from app.services.bigset_import_service import (
    BigSetImportService,
    import_changed_files_in_dir,
    list_mapping_ids,
    preview_import,
)
from app.services.bigset_remote_service import (
    _goal_cache_path,
    maybe_request_dataset_build,
)
from app.services.db_service import (
    DatabaseService,
    get_db_session,
)
from app.services.discovery_query_service import search_imported_jobs
from app.services.job_board_scraper import (
    get_available_sources,
    search_all_sources,
)
from app.services.job_fit_service import rank_imported_jobs
from app.services.search_service import SearchService
from app.services.user_profile_service import load_user_profile
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/discovery", tags=["Job Discovery"])


class DiscoverySearchRequest(BaseModel):
    query: str
    location: str = ""
    limit: int = Field(default=20, ge=1, le=100)
    sources: list[str] | None = None


class IndexJobsRequest(BaseModel):
    jobs: list[dict]


class RemoteTriggerRequest(BaseModel):
    force: bool = False


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


@router.get("/jobs/ranked")
async def ranked_imported_jobs(
    limit: int = 20,
    min_score: float | None = None,
    query: str = "",
    _user: User = Depends(get_current_user_dependency),
):
    """Ranked imported (BigSet) jobs by profile fit; optional semantic query."""
    limit = min(max(limit, 1), 100)
    if query.strip():
        results = await search_imported_jobs(query, limit=limit)
        return {"success": True, "count": len(results), "jobs": results}

    db = get_db_session()
    try:
        profile = load_user_profile()
        jobs = rank_imported_jobs(
            db,
            profile,
            limit=limit,
            min_score=min_score,
        )
        return {"success": True, "count": len(jobs), "jobs": jobs}
    finally:
        db.close()


@router.post("/bigset/sync")
async def bigset_sync(
    _user: User = Depends(get_current_user_dependency),
):
    """Import changed files from BIGSET_IMPORT_DIR."""
    results = await import_changed_files_in_dir()
    return {
        "success": True,
        "files_processed": len(results),
        "results": [r.model_dump() for r in results],
    }


@router.get("/bigset/mappings")
async def bigset_mappings():
    """List BigSet CSV column mapping profiles."""
    return {"success": True, "mappings": list_mapping_ids()}


@router.post("/bigset/preview")
async def bigset_preview(
    file: UploadFile = File(...),
    mapping_id: str | None = Form(None),
    _user: User = Depends(get_current_user_dependency),
):
    """Preview CSV/XLSX columns against a mapping without importing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    max_bytes = getattr(settings, "BIGSET_MAX_UPLOAD_BYTES", 52_428_800)
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size ({max_bytes} bytes)",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    result = preview_import(content, file.filename, mapping_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("errors", result))
    return {"success": True, **result}


@router.get("/bigset/remote/status")
async def bigset_remote_status(
    _user: User = Depends(get_current_user_dependency),
):
    """Remote BigSet automation configuration and cached dataset goal."""
    import os

    goal_path = _goal_cache_path()
    cached_goal = ""
    if goal_path.exists():
        cached_goal = goal_path.read_text(encoding="utf-8").strip()

    return {
        "success": True,
        "remote_enabled": getattr(settings, "BIGSET_REMOTE_ENABLED", False),
        "app_url": getattr(settings, "BIGSET_APP_URL", ""),
        "tinyfish_configured": bool(
            os.getenv("TINYFISH_API_KEY") or getattr(settings, "TINYFISH_API_KEY", None)
        ),
        "cached_goal": cached_goal,
        "goal_path": str(goal_path),
    }


@router.post("/bigset/remote/trigger")
async def bigset_remote_trigger(
    request: RemoteTriggerRequest,
    _user: User = Depends(get_current_user_dependency),
):
    """Trigger optional TinyFish automation against the configured BigSet app URL."""
    profile = load_user_profile()
    result = await maybe_request_dataset_build(profile, force=request.force)
    return {
        "success": True,
        "result": {
            "goal": result.goal,
            "attempted": result.attempted,
            "success": result.success,
            "message": result.message,
            "errors": result.errors,
        },
    }


@router.post("/bigset/import")
async def bigset_import(
    file: UploadFile = File(...),
    mapping_id: str | None = Form(None),
    _user: User = Depends(get_current_user_dependency),
):
    """Import a BigSet CSV/XLSX export into startups and job discovery tables."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    max_bytes = getattr(settings, "BIGSET_MAX_UPLOAD_BYTES", 52_428_800)
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size ({max_bytes} bytes)",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    db = get_db_session()
    try:
        svc = BigSetImportService(db)
        result = await svc.import_file(content, file.filename, mapping_id)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.errors)
        return {"success": True, **result.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("BigSet import error: {}", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        db.close()
