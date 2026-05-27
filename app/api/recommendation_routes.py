"""FastAPI router for job recommendations."""

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.services.db_service import DatabaseService, get_db_session
from app.services.recommendation_service import RecommendationService
from app.services.search_service import SearchService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/jobs/{resume_id}")
async def recommend_jobs(resume_id: int, limit: int = 10):
    """Recommend jobs for a given resume using vector similarity."""
    db = get_db_session()
    try:
        vs = get_vector_store()
        if not vs.is_available:
            raise HTTPException(
                status_code=503, detail="Vector store unavailable — qdrant-client not installed"
            )
        search_svc = SearchService(vector_store=vs)
        db_svc = DatabaseService(db)
        service = RecommendationService(search_service=search_svc, db_service=db_svc)
        results = await service.recommend_jobs_for_resume(resume_id, limit=limit)
        return {"success": True, "count": len(results), "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/resumes/{job_id}")
async def recommend_resumes(job_id: int, limit: int = 10):
    """Recommend resumes for a given job posting using vector similarity."""
    db = get_db_session()
    try:
        vs = get_vector_store()
        if not vs.is_available:
            raise HTTPException(
                status_code=503, detail="Vector store unavailable — qdrant-client not installed"
            )
        search_svc = SearchService(vector_store=vs)
        db_svc = DatabaseService(db)
        service = RecommendationService(search_service=search_svc, db_service=db_svc)
        results = await service.recommend_resumes_for_job(job_id, limit=limit)
        return {"success": True, "count": len(results), "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/skill-gap/{resume_id}/{job_id}")
async def skill_gap(resume_id: int, job_id: int):
    """Skill gap analysis between a resume and a job posting."""
    db = get_db_session()
    try:
        vs = get_vector_store()
        if not vs.is_available:
            raise HTTPException(
                status_code=503, detail="Vector store unavailable — qdrant-client not installed"
            )
        search_svc = SearchService(vector_store=vs)
        db_svc = DatabaseService(db)
        service = RecommendationService(search_service=search_svc, db_service=db_svc)
        result = service.get_skill_gap_analysis(resume_id, job_id)
        return {"success": True, "analysis": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Skill gap analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/career/{resume_id}")
async def career_suggestions(resume_id: int):
    """Career suggestions based on resume skills and trending job requirements."""
    db = get_db_session()
    try:
        vs = get_vector_store()
        if not vs.is_available:
            raise HTTPException(
                status_code=503, detail="Vector store unavailable — qdrant-client not installed"
            )
        search_svc = SearchService(vector_store=vs)
        db_svc = DatabaseService(db)
        service = RecommendationService(search_service=search_svc, db_service=db_svc)
        result = service.get_career_suggestions(resume_id)
        return {"success": True, "suggestions": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Career suggestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
