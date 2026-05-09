"""FastAPI router for application tracking."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from app.services.db_service import DatabaseService, get_db_session
from app.services.tracking_service import VALID_STATUSES, ApplicationTracker

router = APIRouter(prefix="/applications", tags=["Application Tracking"])


class TrackApplicationRequest(BaseModel):
    user_id: Optional[int] = None
    job_id: Optional[int] = None
    resume_id: Optional[int] = None
    company_name: str = ""
    position_title: str = ""
    status: str = Field(default="applied")
    notes: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None


@router.post("")
async def track_application(request: TrackApplicationRequest):
    """Track a new job application."""
    db = get_db_session()
    try:
        tracker = ApplicationTracker(db_service=DatabaseService(db))
        data = request.model_dump(exclude_none=True)
        app_id = tracker.track_application(data)
        if app_id is None:
            raise HTTPException(status_code=400, detail="Failed to track application")
        return {"success": True, "id": app_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Track application error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("")
async def list_applications(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List applications with optional status filter."""
    db = get_db_session()
    try:
        tracker = ApplicationTracker(db_service=DatabaseService(db))
        apps = tracker.get_applications(
            user_id=user_id, status=status, limit=limit, offset=offset
        )
        return {"success": True, "count": len(apps), "applications": apps}
    except Exception as e:
        logger.error(f"List applications error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.put("/{app_id}")
async def update_application(app_id: int, request: UpdateStatusRequest):
    """Update application status."""
    if request.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )
    db = get_db_session()
    try:
        tracker = ApplicationTracker(db_service=DatabaseService(db))
        success = tracker.update_status(app_id, request.status, request.notes)
        if not success:
            raise HTTPException(
                status_code=404, detail="Application not found or update failed"
            )
        return {
            "success": True,
            "message": f"Application {app_id} updated to '{request.status}'",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update application error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.delete("/{app_id}")
async def delete_application(app_id: int):
    """Delete an application."""
    db = get_db_session()
    try:
        tracker = ApplicationTracker(db_service=DatabaseService(db))
        success = tracker.delete_application(app_id)
        if not success:
            raise HTTPException(status_code=404, detail="Application not found")
        return {"success": True, "message": f"Application {app_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete application error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/stats")
async def application_stats(user_id: Optional[int] = None):
    """Get application statistics."""
    db = get_db_session()
    try:
        tracker = ApplicationTracker(db_service=DatabaseService(db))
        stats = tracker.get_application_stats(user_id=user_id)
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Application stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
