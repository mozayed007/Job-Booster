"""FastAPI router for search & indexing endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from app.services.db_service import DatabaseService, get_db_session
from app.services.search_service import SearchService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    query: str
    n_results: int = Field(default=10, ge=1, le=100)


class HybridSearchRequest(BaseModel):
    query: str
    collection: str = Field(pattern="^(resumes|jobs|cover_letters)$")
    n_results: int = Field(default=10, ge=1, le=100)


class IndexDocumentRequest(BaseModel):
    text: str
    metadata: dict[str, Any] | None = None


def _get_search_service() -> SearchService:
    vs = get_vector_store()
    if not vs.is_available:
        raise HTTPException(
            status_code=503, detail="Vector store unavailable — qdrant-client not installed"
        )
    return SearchService(vector_store=vs)


@router.post("/resumes")
async def search_resumes(request: SearchRequest):
    """Search resumes by semantic similarity."""
    try:
        service = _get_search_service()
        results = await service.search_resumes(request.query, request.n_results)
        return {"success": True, "count": len(results), "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume search error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/jobs")
async def search_jobs(request: SearchRequest):
    """Search jobs by semantic similarity."""
    try:
        service = _get_search_service()
        results = await service.search_jobs(request.query, request.n_results)
        return {"success": True, "count": len(results), "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job search error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/hybrid")
async def hybrid_search(request: HybridSearchRequest):
    """Hybrid search combining vector similarity + keyword matching."""
    try:
        vs = get_vector_store()
        if not vs.is_available:
            raise HTTPException(status_code=503, detail="Vector store unavailable")

        db = get_db_session()
        try:
            db_service = DatabaseService(db)
            service = SearchService(vector_store=vs, db_service=db_service)
            results = await service.hybrid_search(
                request.query, request.collection, request.n_results
            )
        finally:
            db.close()

        return {"success": True, "count": len(results), "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/index/resume/{resume_id}")
async def index_resume(resume_id: int, request: IndexDocumentRequest):
    """Index a resume in the vector store."""
    try:
        vs = get_vector_store()
        if not vs.is_available:
            raise HTTPException(status_code=503, detail="Vector store unavailable")

        service = SearchService(vector_store=vs)
        await service.index_resume(resume_id, request.text, request.metadata)
        return {"success": True, "message": f"Resume {resume_id} indexed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume indexing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/index/job/{job_id}")
async def index_job(job_id: int, request: IndexDocumentRequest):
    """Index a job posting in the vector store."""
    try:
        vs = get_vector_store()
        if not vs.is_available:
            raise HTTPException(status_code=503, detail="Vector store unavailable")

        service = SearchService(vector_store=vs)
        await service.index_job(job_id, request.text, request.metadata)
        return {"success": True, "message": f"Job {job_id} indexed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job indexing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_stats():
    """Get vector store collection statistics."""
    try:
        vs = get_vector_store()
        return {"success": True, "stats": vs.get_all_stats()}
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
