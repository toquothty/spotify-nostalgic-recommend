"""
Progress tracking service for real-time analysis updates
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.models_extended import AnalysisProgress

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Service for tracking and updating analysis progress"""

    def __init__(self):
        self._progress_cache: Dict[int, Dict[str, Any]] = {}

    def start_analysis(self, user_id: int, total_tracks: int, db: Session) -> str:
        """Start tracking analysis progress for a user"""
        try:
            # Create or update progress record
            progress = (
                db.query(AnalysisProgress)
                .filter(AnalysisProgress.user_id == user_id)
                .first()
            )

            if progress:
                # Update existing progress
                progress.status = "starting"
                progress.current_step = "Initializing analysis"
                progress.progress_percentage = 0
                progress.tracks_processed = 0
                progress.total_tracks = total_tracks
                progress.error_message = None
                progress.started_at = datetime.utcnow()
                progress.completed_at = None
                progress.updated_at = datetime.utcnow()
            else:
                # Create new progress record
                progress = AnalysisProgress(
                    user_id=user_id,
                    status="starting",
                    current_step="Initializing analysis",
                    progress_percentage=0,
                    tracks_processed=0,
                    total_tracks=total_tracks,
                    started_at=datetime.utcnow(),
                )
                db.add(progress)

            db.commit()
            db.refresh(progress)

            # Cache the progress (include error_message to ensure it's cleared)
            self._progress_cache[user_id] = {
                "status": progress.status,
                "current_step": progress.current_step,
                "progress_percentage": progress.progress_percentage,
                "tracks_processed": progress.tracks_processed,
                "total_tracks": progress.total_tracks,
                "error_message": None,  # Explicitly clear error message
                "started_at": progress.started_at.isoformat(),
                "updated_at": progress.updated_at.isoformat(),
            }

            logger.info(
                f"Started analysis tracking for user {user_id} with {total_tracks} tracks"
            )
            return "started"

        except Exception as e:
            logger.error(f"Failed to start analysis tracking: {e}")
            return "error"

    def update_progress(
        self,
        user_id: int,
        status: str,
        current_step: str,
        tracks_processed: int = 0,
        progress_percentage: Optional[int] = None,
        db: Session = None,
    ):
        """Update analysis progress"""
        try:
            # Calculate progress percentage if not provided
            if progress_percentage is None and user_id in self._progress_cache:
                total_tracks = self._progress_cache[user_id].get("total_tracks", 1)
                progress_percentage = min(
                    100, int((tracks_processed / total_tracks) * 100)
                )

            # Update cache
            if user_id in self._progress_cache:
                self._progress_cache[user_id].update(
                    {
                        "status": status,
                        "current_step": current_step,
                        "progress_percentage": progress_percentage or 0,
                        "tracks_processed": tracks_processed,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                )

            # Update database if session provided
            if db:
                progress = (
                    db.query(AnalysisProgress)
                    .filter(AnalysisProgress.user_id == user_id)
                    .first()
                )

                if progress:
                    progress.status = status
                    progress.current_step = current_step
                    progress.progress_percentage = progress_percentage or 0
                    progress.tracks_processed = tracks_processed
                    progress.updated_at = datetime.utcnow()

                    if status in ["completed", "failed"]:
                        progress.completed_at = datetime.utcnow()

                    db.commit()

            logger.info(
                f"Updated progress for user {user_id}: {status} - {current_step} ({progress_percentage}%)"
            )

        except Exception as e:
            logger.error(f"Failed to update progress for user {user_id}: {e}")

    def set_error(self, user_id: int, error_message: str, db: Session):
        """Set error status for analysis"""
        try:
            self.update_progress(
                user_id=user_id,
                status="failed",
                current_step="Analysis failed",
                progress_percentage=0,
                db=db,
            )

            # Update error message in database
            progress = (
                db.query(AnalysisProgress)
                .filter(AnalysisProgress.user_id == user_id)
                .first()
            )

            if progress:
                progress.error_message = error_message
                progress.completed_at = datetime.utcnow()
                db.commit()

            # Update cache
            if user_id in self._progress_cache:
                self._progress_cache[user_id]["error_message"] = error_message

            logger.error(f"Set error for user {user_id}: {error_message}")

        except Exception as e:
            logger.error(f"Failed to set error for user {user_id}: {e}")

    def complete_analysis(
        self, user_id: int, final_track_count: int, cluster_count: int, db: Session
    ):
        """Mark analysis as completed"""
        try:
            self.update_progress(
                user_id=user_id,
                status="completed",
                current_step=f"Analysis complete! {final_track_count} tracks analyzed into {cluster_count} clusters",
                tracks_processed=final_track_count,
                progress_percentage=100,
                db=db,
            )

            logger.info(
                f"Completed analysis for user {user_id}: {final_track_count} tracks, {cluster_count} clusters"
            )

        except Exception as e:
            logger.error(f"Failed to complete analysis for user {user_id}: {e}")

    def get_progress(self, user_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """Get current progress for a user"""
        try:
            # Try cache first
            if user_id in self._progress_cache:
                return self._progress_cache[user_id]

            # Fall back to database
            progress = (
                db.query(AnalysisProgress)
                .filter(AnalysisProgress.user_id == user_id)
                .first()
            )

            if progress:
                progress_data = {
                    "status": progress.status,
                    "current_step": progress.current_step,
                    "progress_percentage": progress.progress_percentage,
                    "tracks_processed": progress.tracks_processed,
                    "total_tracks": progress.total_tracks,
                    "error_message": progress.error_message,
                    "started_at": (
                        progress.started_at.isoformat() if progress.started_at else None
                    ),
                    "completed_at": (
                        progress.completed_at.isoformat()
                        if progress.completed_at
                        else None
                    ),
                    "updated_at": (
                        progress.updated_at.isoformat() if progress.updated_at else None
                    ),
                }

                # Update cache
                self._progress_cache[user_id] = progress_data
                return progress_data

            return None

        except Exception as e:
            logger.error(f"Failed to get progress for user {user_id}: {e}")
            return None

    def clear_progress(self, user_id: int):
        """Clear progress from cache"""
        if user_id in self._progress_cache:
            del self._progress_cache[user_id]

    def get_all_active_progress(self) -> Dict[int, Dict[str, Any]]:
        """Get all active progress tracking"""
        return {
            user_id: progress
            for user_id, progress in self._progress_cache.items()
            if progress.get("status")
            in ["starting", "fetching_tracks", "getting_features", "clustering"]
        }


# Global progress tracker instance
progress_tracker = ProgressTracker()
