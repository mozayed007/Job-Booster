"""FastAPI router for enjoyable gap recommendations.

Bridges the canonical skill-gap analysis (RecommendationService) with the
user's personal context (onboarding) to produce projects/courses the user
will actually enjoy. Personal context is read ONLY here by this agent —
resume and cover-letter agents never access it.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from app.middleware.auth_middleware import optional_user_dependency
from app.models.db_models import User
from app.services.db_service import DatabaseService, get_db_session
from app.services.recommendation_service import RecommendationService
from app.services.search_service import SearchService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _extract_personal_context(user: User | None) -> dict[str, Any]:
    """Pull personal_context from the user's profile_json, if present."""
    if user is None:
        return {}
    profile = user.profile_json or {}
    context = profile.get("personal_context")
    return context if isinstance(context, dict) else {}


@router.get("/enjoyable/{resume_id}/{job_id}")
async def enjoyable_recommendations(
    resume_id: int,
    job_id: int,
    user: User | None = Depends(optional_user_dependency),
    max_per_gap: int = Query(3, ge=1, le=5, description="Max recommendations per gap"),
):
    """Generate enjoyable project/course recommendations covering skill gaps.

    Combines the canonical skill-gap analysis with the user's personal context
    (if onboarding was completed) to recommend projects and courses the user
    will genuinely enjoy. Falls back to broadly engaging recs when no personal
    context is available; gaps that cannot be mapped are surfaced honestly in
    uncovered_gaps.
    """
    db = get_db_session()
    try:
        vs = get_vector_store()
        search_svc = SearchService(vector_store=vs)
        db_svc = DatabaseService(db)
        rec_svc = RecommendationService(search_service=search_svc, db_service=db_svc)

        # 1. Get the canonical skill gaps (set-difference on content_json).
        gap_analysis = rec_svc.get_skill_gap_analysis(resume_id, job_id)
        if "error" in gap_analysis:
            raise HTTPException(status_code=404, detail=gap_analysis["error"])

        gaps: list[str] = list(gap_analysis.get("gaps", []))
        if not gaps:
            return {
                "success": True,
                "gap_analysis": gap_analysis,
                "recommendations": [],
                "summary": "No skill gaps found — your resume covers all required skills.",
                "uncovered_gaps": [],
                "has_personal_context": False,
            }

        # 2. Pull the user's personal context (only this agent reads it).
        personal_context = _extract_personal_context(user)

        # 3. Build lightly-scoped job context from the gap analysis.
        job_context = f"Resume_id={resume_id}, Job_id={job_id}"

        # 4. Run the gap-recommendation agent.
        from app.agents.gap_recommendation import recommend_gaps

        result = await recommend_gaps(gaps, personal_context, job_context)

        # Enforce the max_per_gap cap from the query parameter.
        if max_per_gap and result.recommendations:
            capped: dict[str, list] = {}
            for rec in result.recommendations:
                capped.setdefault(rec.target_gap, []).append(rec)
            trimmed = []
            for gap_recs in capped.values():
                trimmed.extend(gap_recs[:max_per_gap])
            result.recommendations = trimmed

        return {
            "success": True,
            "gap_analysis": gap_analysis,
            "recommendations": [r.model_dump() for r in result.recommendations],
            "summary": result.summary,
            "uncovered_gaps": result.uncovered_gaps,
            "has_personal_context": bool(personal_context),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enjoyable recommendations error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()
