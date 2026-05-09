"""Application tracking service for managing job applications."""

from typing import Any, Optional

from loguru import logger
from sqlalchemy import func

from app.models.db_models import ApplicationDB
from app.services.db_service import DatabaseService, get_db_session

VALID_STATUSES = {"applied", "interview", "offer", "rejected", "withdrawn"}


class ApplicationTracker:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def track_application(self, data: dict[str, Any]) -> Optional[int]:
        status = data.get("status", "applied")
        if status not in VALID_STATUSES:
            logger.warning(f"Invalid status '{status}', defaulting to 'applied'")
            status = "applied"
        data["status"] = status
        record_id = self.db_service.insert_record("applications", data)
        if record_id:
            logger.info(f"Tracked application id={record_id}")
        return record_id

    def update_status(self, app_id: int, status: str, notes: Optional[str] = None) -> bool:
        if status not in VALID_STATUSES:
            logger.error(f"Invalid status: {status}")
            return False
        try:
            db = self.db_service.db
            app = db.query(ApplicationDB).filter(ApplicationDB.id == app_id).first()
            if not app:
                logger.warning(f"Application {app_id} not found")
                return False
            app.status = status
            if notes is not None:
                app.notes = notes
            db.commit()
            logger.info(f"Updated application {app_id} -> {status}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating application {app_id}: {e}")
            return False

    def get_applications(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        try:
            db = self.db_service.db
            query = db.query(ApplicationDB)
            if user_id is not None:
                query = query.filter(ApplicationDB.user_id == user_id)
            if status:
                query = query.filter(ApplicationDB.status == status)
            apps = query.order_by(ApplicationDB.applied_at.desc()).offset(offset).limit(limit).all()
            return [self._to_dict(app) for app in apps]
        except Exception as e:
            logger.error(f"Error fetching applications: {e}")
            return []

    def get_application_stats(self, user_id: Optional[int] = None) -> dict[str, Any]:
        try:
            db = self.db_service.db
            query = db.query(ApplicationDB)
            if user_id is not None:
                query = query.filter(ApplicationDB.user_id == user_id)

            total = query.count()
            status_counts = db.query(ApplicationDB.status, func.count(ApplicationDB.id))
            if user_id is not None:
                status_counts = status_counts.filter(ApplicationDB.user_id == user_id)
            status_counts = status_counts.group_by(ApplicationDB.status).all()

            by_status = {status: count for status, count in status_counts}

            return {
                "total": total,
                "by_status": by_status,
                "applied": by_status.get("applied", 0),
                "interview": by_status.get("interview", 0),
                "offer": by_status.get("offer", 0),
                "rejected": by_status.get("rejected", 0),
                "withdrawn": by_status.get("withdrawn", 0),
            }
        except Exception as e:
            logger.error(f"Error computing application stats: {e}")
            return {"total": 0, "by_status": {}}

    def delete_application(self, app_id: int) -> bool:
        try:
            db = self.db_service.db
            app = db.query(ApplicationDB).filter(ApplicationDB.id == app_id).first()
            if not app:
                logger.warning(f"Application {app_id} not found")
                return False
            db.delete(app)
            db.commit()
            logger.info(f"Deleted application {app_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting application {app_id}: {e}")
            return False

    @staticmethod
    def _to_dict(app: ApplicationDB) -> dict[str, Any]:
        return {
            "id": app.id,
            "user_id": app.user_id,
            "job_id": app.job_id,
            "resume_id": app.resume_id,
            "company_name": app.company_name,
            "position_title": app.position_title,
            "status": app.status,
            "notes": app.notes,
            "applied_at": str(app.applied_at) if app.applied_at else None,
            "updated_at": str(app.updated_at) if app.updated_at else None,
        }


def get_application_tracker(db_service: Optional[DatabaseService] = None) -> ApplicationTracker:
    if db_service is None:
        db = get_db_session()
        db_service = DatabaseService(db)
    return ApplicationTracker(db_service=db_service)
