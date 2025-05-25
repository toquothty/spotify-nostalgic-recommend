"""
Progress tracking API endpoints for real-time analysis updates
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.models import User
from app.api.auth import get_current_session
from app.services.progress_tracker import progress_tracker

router = APIRouter()


@router.get("/analysis/{session_id}")
async def get_analysis_progress(
    session_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get real-time analysis progress for a user"""
    try:
        session = get_current_session(session_id, db)
        user = db.query(User).filter(User.id == session.user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get progress from tracker
        progress = progress_tracker.get_progress(user.id, db)

        if not progress:
            return {
                "status": "not_started",
                "current_step": "Analysis not started",
                "progress_percentage": 0,
                "tracks_processed": 0,
                "total_tracks": 0,
                "error_message": None,
                "started_at": None,
                "completed_at": None,
                "updated_at": None,
            }

        return progress

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.get("/all-active")
async def get_all_active_progress() -> Dict[str, Any]:
    """Get all active analysis progress (for admin/debugging)"""
    try:
        active_progress = progress_tracker.get_all_active_progress()
        return {"active_analyses": len(active_progress), "progress": active_progress}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get active progress: {str(e)}"
        )
