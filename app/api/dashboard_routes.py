"""Dashboard aggregation endpoint — single call for all dashboard data."""

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.services.analytics_service import AnalyticsService
from app.services.db_service import DatabaseService, get_db_session
from app.services.recommendation_service import RecommendationService
from app.services.search_service import SearchService
from app.services.tracking_service import ApplicationTracker
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
async def get_dashboard(user_id: int | None = None, resume_id: int | None = None):
    """Aggregated dashboard data in a single call.

    Returns: profile summary, application funnel, recent applications,
    top matches, skill gaps, and quick-action metadata.
    """
    db = get_db_session()
    try:
        db_svc = DatabaseService(db)
        analytics = AnalyticsService(db_service=db_svc)
        tracker = ApplicationTracker(db_service=db_svc)

        # Application stats
        app_stats = tracker.get_application_stats(user_id=user_id)

        # Recent applications (last 10)
        recent_apps = tracker.get_applications(user_id=user_id, limit=10)

        # Analytics dashboard data
        dashboard = analytics.get_dashboard_data(user_id=user_id)

        # Resume count
        resume_count = dashboard.get("resumes", {}).get("total_resumes", 0)
        job_count = dashboard.get("jobs", {}).get("total_jobs", 0)

        # Top matches (if resume_id provided)
        top_matches = []
        if resume_id:
            try:
                vs = get_vector_store()
                if vs.is_available:
                    search_svc = SearchService(vector_store=vs, db_service=db_svc)
                    rec_svc = RecommendationService(search_service=search_svc, db_service=db_svc)
                    top_matches = await rec_svc.recommend_jobs_for_resume(resume_id, limit=5)
            except Exception as e:
                logger.warning(f"Top matches fetch failed: {e}")

        # Skill gaps (aggregate from analytics)
        skill_trends = dashboard.get("skill_trends", {})

        return {
            "success": True,
            "data": {
                "profile": {
                    "resume_count": resume_count,
                    "job_count": job_count,
                    "application_count": app_stats.get("total", 0),
                },
                "application_funnel": app_stats,
                "recent_applications": recent_apps,
                "top_matches": top_matches[:5],
                "skill_trends": skill_trends.get("top_skills", [])[:10],
                "resume_stats": dashboard.get("resumes", {}),
                "job_stats": dashboard.get("jobs", {}),
                "scanner_stats": dashboard.get("scanner", {}),
            },
        }
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
