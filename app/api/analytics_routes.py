"""FastAPI router for analytics dashboard."""

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.services.analytics_service import AnalyticsService
from app.services.db_service import DatabaseService, get_db_session

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
async def dashboard(user_id: int | None = None):
    """Full analytics dashboard data."""
    db = get_db_session()
    try:
        service = AnalyticsService(db_service=DatabaseService(db))
        data = service.get_dashboard_data(user_id=user_id)
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/resumes")
async def resume_stats():
    """Resume statistics."""
    db = get_db_session()
    try:
        service = AnalyticsService(db_service=DatabaseService(db))
        stats = service.get_resume_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Resume stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/jobs")
async def job_stats():
    """Job statistics."""
    db = get_db_session()
    try:
        service = AnalyticsService(db_service=DatabaseService(db))
        stats = service.get_job_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Job stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/skills")
async def skill_trends():
    """Skill trends across all job postings."""
    db = get_db_session()
    try:
        service = AnalyticsService(db_service=DatabaseService(db))
        trends = service.get_skill_trends()
        return {"success": True, "trends": trends}
    except Exception as e:
        logger.error(f"Skill trends error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@router.get("/scanner")
async def scanner_stats():
    """Startup scanner statistics."""
    db = get_db_session()
    try:
        service = AnalyticsService(db_service=DatabaseService(db))
        stats = service.get_scanner_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Scanner stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()
