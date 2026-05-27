"""Analytics dashboard service for Job_Booster."""

from collections import Counter
from typing import Any

from loguru import logger
from sqlalchemy import func

from app.models.db_models import (
    ApplicationDB,
    JobPostingDB,
    ResumeDB,
    ResumeVersionDB,
    ScannedJobDB,
    ScannerStateDB,
    StartupDB,
    TailoredResumeDB,
)
from app.services.db_service import DatabaseService, get_db_session


class AnalyticsService:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def get_resume_stats(self) -> dict[str, Any]:
        try:
            db = self.db_service.db
            resume_count = db.query(func.count(ResumeDB.id)).scalar() or 0
            version_count = db.query(func.count(ResumeVersionDB.id)).scalar() or 0
            tailored_count = db.query(func.count(TailoredResumeDB.id)).scalar() or 0

            parsed_with_skills = 0
            resumes = db.query(ResumeDB.content_json).all()
            for (content_json,) in resumes:
                if content_json and isinstance(content_json, dict):
                    for key in ("skills", "technologies", "tools"):
                        if key in content_json and content_json[key]:
                            parsed_with_skills += 1
                            break

            return {
                "total_resumes": resume_count,
                "total_versions": version_count,
                "total_tailored": tailored_count,
                "parsed_with_skills": parsed_with_skills,
            }
        except Exception as e:
            logger.error(f"Error computing resume stats: {e}")
            return {
                "total_resumes": 0,
                "total_versions": 0,
                "total_tailored": 0,
                "parsed_with_skills": 0,
            }

    def get_job_stats(self) -> dict[str, Any]:
        try:
            db = self.db_service.db
            job_count = db.query(func.count(JobPostingDB.id)).scalar() or 0
            company_count = (
                db.query(func.count(func.distinct(JobPostingDB.company)))
                .filter(JobPostingDB.company.isnot(None))
                .scalar()
                or 0
            )

            skill_counter: Counter[str] = Counter()
            jobs = db.query(JobPostingDB.content_json).all()
            for (content_json,) in jobs:
                if content_json and isinstance(content_json, dict):
                    for key in ("skills", "technologies", "tools"):
                        val = content_json.get(key)
                        if isinstance(val, list):
                            for s in val:
                                skill_counter[str(s).lower()] += 1

            top_skills = [s for s, _ in skill_counter.most_common(20)]

            return {
                "total_jobs": job_count,
                "total_companies": company_count,
                "top_skills": top_skills,
                "unique_skills": len(skill_counter),
            }
        except Exception as e:
            logger.error(f"Error computing job stats: {e}")
            return {"total_jobs": 0, "total_companies": 0, "top_skills": [], "unique_skills": 0}

    def get_matching_stats(self) -> dict[str, Any]:
        try:
            db = self.db_service.db
            scores = (
                db.query(TailoredResumeDB.match_score)
                .filter(TailoredResumeDB.match_score.isnot(None))
                .all()
            )
            score_values = [s[0] for s in scores if s[0] is not None]

            avg_score = sum(score_values) / len(score_values) if score_values else 0
            max_score = max(score_values) if score_values else 0
            min_score = min(score_values) if score_values else 0

            return {
                "total_matches": len(score_values),
                "average_score": round(avg_score, 2),
                "max_score": round(max_score, 2),
                "min_score": round(min_score, 2),
            }
        except Exception as e:
            logger.error(f"Error computing matching stats: {e}")
            return {"total_matches": 0, "average_score": 0, "max_score": 0, "min_score": 0}

    def get_application_funnel(self, user_id: int | None = None) -> dict[str, Any]:
        try:
            db = self.db_service.db
            query = db.query(ApplicationDB.status, func.count(ApplicationDB.id))
            if user_id is not None:
                query = query.filter(ApplicationDB.user_id == user_id)
            status_counts = query.group_by(ApplicationDB.status).all()

            by_status = {status: count for status, count in status_counts}
            total = sum(by_status.values())

            return {
                "total": total,
                "applied": by_status.get("applied", 0),
                "interview": by_status.get("interview", 0),
                "offer": by_status.get("offer", 0),
                "rejected": by_status.get("rejected", 0),
                "withdrawn": by_status.get("withdrawn", 0),
                "interview_rate": round(by_status.get("interview", 0) / total * 100, 1)
                if total
                else 0,
                "offer_rate": round(by_status.get("offer", 0) / total * 100, 1) if total else 0,
            }
        except Exception as e:
            logger.error(f"Error computing application funnel: {e}")
            return {
                "total": 0,
                "applied": 0,
                "interview": 0,
                "offer": 0,
                "rejected": 0,
                "withdrawn": 0,
            }

    def get_skill_trends(self) -> dict[str, Any]:
        try:
            db = self.db_service.db
            skill_counter: Counter[str] = Counter()
            jobs = db.query(JobPostingDB.content_json).all()
            for (content_json,) in jobs:
                if content_json and isinstance(content_json, dict):
                    for key in ("skills", "technologies", "tools"):
                        val = content_json.get(key)
                        if isinstance(val, list):
                            for s in val:
                                skill_counter[str(s).lower()] += 1

            top = skill_counter.most_common(30)
            return {
                "total_skills_tracked": len(skill_counter),
                "top_skills": [{"skill": s, "count": c} for s, c in top],
            }
        except Exception as e:
            logger.error(f"Error computing skill trends: {e}")
            return {"total_skills_tracked": 0, "top_skills": []}

    def get_scanner_stats(self) -> dict[str, Any]:
        try:
            db = self.db_service.db
            startup_count = db.query(func.count(StartupDB.id)).scalar() or 0
            scanned_job_count = db.query(func.count(ScannedJobDB.id)).scalar() or 0
            applied_count = (
                db.query(func.count(ScannedJobDB.id))
                .filter(ScannedJobDB.is_applied.is_(True))
                .scalar()
                or 0
            )

            state = db.query(ScannerStateDB).order_by(ScannerStateDB.id.desc()).first()
            current_batch = state.batch_number if state else 0
            scanner_status = state.status if state else "idle"

            category_counts = (
                db.query(StartupDB.category, func.count(StartupDB.id))
                .group_by(StartupDB.category)
                .all()
            )

            return {
                "total_startups": startup_count,
                "total_scanned_jobs": scanned_job_count,
                "jobs_applied": applied_count,
                "current_batch": current_batch,
                "scanner_status": scanner_status,
                "by_category": {cat: cnt for cat, cnt in category_counts if cat},
            }
        except Exception as e:
            logger.error(f"Error computing scanner stats: {e}")
            return {"total_startups": 0, "total_scanned_jobs": 0, "jobs_applied": 0}

    def get_dashboard_data(self, user_id: int | None = None) -> dict[str, Any]:
        return {
            "resumes": self.get_resume_stats(),
            "jobs": self.get_job_stats(),
            "matching": self.get_matching_stats(),
            "applications": self.get_application_funnel(user_id),
            "skill_trends": self.get_skill_trends(),
            "scanner": self.get_scanner_stats(),
        }


def get_analytics_service(db_service: DatabaseService | None = None) -> AnalyticsService:
    if db_service is None:
        db = get_db_session()
        db_service = DatabaseService(db)
    return AnalyticsService(db_service=db_service)
