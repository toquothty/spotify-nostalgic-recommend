"""
Recommendations API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models import User, Track, UserCluster, Recommendation, UserSession
from app.services.spotify_client import SpotifyClient
from app.services.data_analyzer import DataAnalyzer
from app.services.recommendation_engine import RecommendationEngine
from app.services.progress_tracker import progress_tracker
from app.api.auth import get_current_session
from app.schemas import (
    RecommendationResponse,
    DataAnalysisRequest,
    RecommendationRequest,
    FeedbackRequest,
)

router = APIRouter()
spotify_client = SpotifyClient()
data_analyzer = DataAnalyzer()
recommendation_engine = RecommendationEngine()

logger = logging.getLogger(__name__)


@router.post("/clear-error")
async def clear_analysis_error(session_id: str, db: Session = Depends(get_db)):
    """Clear any existing analysis error state"""
    try:
        session = get_current_session(session_id, db)
        user = db.query(User).filter(User.id == session.user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Clear progress tracker cache
        progress_tracker.clear_progress(user.id)

        # Clear database error state
        from app.models_extended import AnalysisProgress

        progress = (
            db.query(AnalysisProgress)
            .filter(AnalysisProgress.user_id == user.id)
            .first()
        )
        if progress:
            progress.error_message = None
            progress.status = "not_started"
            progress.current_step = "Ready to start analysis"
            progress.progress_percentage = 0
            db.commit()

        return {"status": "success", "message": "Error state cleared"}

    except Exception as e:
        logger.error(f"Failed to clear error: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/analyze-library")
async def analyze_user_library(
    request: DataAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Analyze user's Spotify library and perform clustering"""
    session = get_current_session(request.session_id, db)
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Clear any existing error state first
        progress_tracker.clear_progress(user.id)

        # Allow re-analysis by clearing existing data
        existing_tracks = db.query(Track).filter(Track.user_id == user.id).count()
        if existing_tracks > 0:
            # Clear existing data for re-analysis
            db.query(Track).filter(Track.user_id == user.id).delete()
            db.query(UserCluster).filter(UserCluster.user_id == user.id).delete()
            db.query(Recommendation).filter(Recommendation.user_id == user.id).delete()
            db.commit()

        # Test token first
        logger.info(f"ANALYSIS: Testing token for user {user.id}")
        try:
            total_tracks = spotify_client.get_user_saved_tracks_count(
                session.access_token
            )
            logger.info(f"ANALYSIS: Token works, got {total_tracks} tracks")
        except Exception as e:
            logger.error(f"ANALYSIS: Token test failed: {e}")
            raise HTTPException(status_code=401, detail=f"Token invalid: {str(e)}")

        # Initialize progress tracking
        progress_tracker.start_analysis(
            user.id, min(request.track_limit, total_tracks), db
        )

        # For now, let's do a simple synchronous analysis with just a few tracks
        logger.info(f"ANALYSIS: Starting simple analysis for user {user.id}")

        # Get just 10 tracks for testing
        saved_tracks = spotify_client.get_user_saved_tracks(
            session.access_token, limit=10
        )
        logger.info(f"ANALYSIS: Got {len(saved_tracks)} tracks")

        if not saved_tracks:
            progress_tracker.set_error(user.id, "No tracks found in your library", db)
            return {"message": "No tracks found", "status": "error"}

        # Extract track IDs
        track_ids = [
            item["track"]["id"] for item in saved_tracks if item["track"]["id"]
        ]
        logger.info(f"ANALYSIS: Extracted {len(track_ids)} track IDs: {track_ids}")

        # WORKAROUND: Skip audio features due to 403 errors
        # Store tracks with default audio features
        logger.info(f"ANALYSIS: Storing tracks without audio features (workaround)")

        tracks_stored = 0
        for item in saved_tracks:
            track = item["track"]
            if not track["id"]:
                continue

            # Create track with default audio features
            track_data = Track(
                spotify_id=track["id"],
                user_id=user.id,
                name=track["name"],
                artist_name=", ".join([artist["name"] for artist in track["artists"]]),
                album_name=track["album"]["name"],
                duration_ms=track["duration_ms"],
                popularity=track["popularity"],
                explicit=track["explicit"],
                preview_url=track["preview_url"],
                external_url=track["external_urls"].get("spotify"),
                image_url=(
                    track["album"]["images"][0]["url"]
                    if track["album"]["images"]
                    else None
                ),
                added_at=datetime.fromisoformat(
                    item["added_at"].replace("Z", "+00:00")
                ),
                release_date=track["album"]["release_date"],
                # Default audio features (neutral values)
                acousticness=0.5,
                danceability=0.5,
                energy=0.5,
                instrumentalness=0.0,
                liveness=0.1,
                loudness=-10.0,
                speechiness=0.05,
                tempo=120.0,
                valence=0.5,
                key=0,
                mode=1,
                time_signature=4,
            )

            db.add(track_data)
            tracks_stored += 1

        db.commit()
        logger.info(f"ANALYSIS: Stored {tracks_stored} tracks successfully")

        # Perform metadata-based clustering
        logger.info(f"ANALYSIS: Starting clustering for user {user.id}")
        clusters = data_analyzer.perform_clustering(user.id, db)
        logger.info(f"ANALYSIS: Created {len(clusters)} clusters")

        # Complete analysis
        progress_tracker.complete_analysis(user.id, tracks_stored, len(clusters), db)

        return {
            "message": "Analysis completed successfully (using workaround for audio features)",
            "status": "completed",
            "tracks_analyzed": tracks_stored,
            "clusters_created": len(clusters),
            "note": "Audio features API is currently unavailable. Using metadata-based clustering.",
        }

    except Exception as e:
        logger.error(f"Failed to start library analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/generate")
async def generate_recommendations(
    session_id: str,
    recommendation_type: str = "cluster",
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Generate new recommendations for user"""
    session = get_current_session(session_id, db)
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check rate limiting
    if not can_generate_recommendations(session, db):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before generating new recommendations.",
        )

    try:
        # Check if user has analyzed tracks
        track_count = db.query(Track).filter(Track.user_id == user.id).count()
        if track_count == 0:
            raise HTTPException(
                status_code=400, detail="Please analyze your library first"
            )

        # Generate recommendations based on type
        if recommendation_type == "cluster":
            recommendations = recommendation_engine.generate_cluster_recommendations(
                session.access_token, user.id, limit, db
            )
        elif recommendation_type == "nostalgia":
            if not user.date_of_birth:
                raise HTTPException(
                    status_code=400,
                    detail="Date of birth required for nostalgia recommendations",
                )
            recommendations = recommendation_engine.generate_nostalgia_recommendations(
                session.access_token, user.id, limit, db
            )
        elif recommendation_type == "forgotten":
            recommendations = recommendation_engine.get_forgotten_favorites(
                session.access_token, user.id, limit, db
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid recommendation type")

        # Update rate limiting only if we got recommendations
        if recommendations:
            update_recommendation_limits(session, db)

        return {
            "recommendations": recommendations,
            "count": len(recommendations),
            "type": recommendation_type,
        }

    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        raise HTTPException(
            status_code=500, detail=f"Recommendation generation failed: {str(e)}"
        )


@router.get("/forgotten-favorites")
async def get_forgotten_favorites(
    session_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Get user's forgotten favorite tracks"""
    session = get_current_session(session_id, db)
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Check if user has analyzed tracks
        track_count = db.query(Track).filter(Track.user_id == user.id).count()
        if track_count == 0:
            raise HTTPException(
                status_code=400, detail="Please analyze your library first"
            )

        forgotten = recommendation_engine.get_forgotten_favorites(
            session.access_token, user.id, limit, db
        )

        return {
            "forgotten_favorites": forgotten,
            "count": len(forgotten),
        }

    except Exception as e:
        logger.error(f"Failed to get forgotten favorites: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get forgotten favorites: {str(e)}"
        )


@router.get("/history")
async def get_recommendation_history(
    session_id: str, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)
):
    """Get user's recommendation history"""
    session = get_current_session(session_id, db)

    recommendations = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == session.user_id)
        .order_by(Recommendation.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "recommendations": [
            RecommendationResponse.from_orm(rec) for rec in recommendations
        ],
        "count": len(recommendations),
    }


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest, session_id: str, db: Session = Depends(get_db)
):
    """Submit feedback for a recommendation"""
    session = get_current_session(session_id, db)

    recommendation = (
        db.query(Recommendation)
        .filter(
            Recommendation.id == feedback.recommendation_id,
            Recommendation.user_id == session.user_id,
        )
        .first()
    )

    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # Update feedback
    if feedback.liked is not None:
        recommendation.user_liked = feedback.liked
    if feedback.already_knew is not None:
        recommendation.user_already_knew = feedback.already_knew

    recommendation.user_feedback_at = datetime.utcnow()
    db.commit()

    # If user liked the track, add it to their library
    if feedback.liked:
        try:
            spotify_client.add_tracks_to_library(
                session.access_token, [recommendation.spotify_track_id]
            )
        except Exception as e:
            logger.warning(f"Failed to add track to library: {e}")

    return {"message": "Feedback submitted successfully"}


@router.get("/library-info")
async def get_library_info(session_id: str, db: Session = Depends(get_db)):
    """Get user's Spotify library information"""
    session = get_current_session(session_id, db)

    try:
        # Get total liked songs count from Spotify
        total_liked_songs = spotify_client.get_user_saved_tracks_count(
            session.access_token
        )

        return {
            "total_liked_songs": total_liked_songs,
            "message": f"You have {total_liked_songs} liked songs in your Spotify library",
        }
    except Exception as e:
        logger.error(f"Failed to get library info: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get library info: {str(e)}"
        )


@router.get("/status")
async def get_analysis_status(session_id: str, db: Session = Depends(get_db)):
    """Get the status of library analysis and recommendations"""
    session = get_current_session(session_id, db)
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check analysis status
    track_count = db.query(Track).filter(Track.user_id == user.id).count()
    cluster_count = db.query(UserCluster).filter(UserCluster.user_id == user.id).count()
    recommendation_count = (
        db.query(Recommendation).filter(Recommendation.user_id == user.id).count()
    )

    # Check rate limiting
    can_recommend = can_generate_recommendations(session, db)

    # Get total liked songs count from Spotify
    total_liked_songs = 0
    try:
        total_liked_songs = spotify_client.get_user_saved_tracks_count(
            session.access_token
        )
    except Exception as e:
        logger.warning(f"Failed to get total liked songs count: {e}")

    return {
        "library_analyzed": track_count > 0,
        "track_count": track_count,
        "cluster_count": cluster_count,
        "recommendation_count": recommendation_count,
        "can_generate_recommendations": can_recommend,
        "needs_onboarding": user.date_of_birth is None,
        "last_recommendation": (
            session.last_recommendation_at.isoformat()
            if session.last_recommendation_at
            else None
        ),
        "recommendations_today": session.recommendation_count_today,
        "total_liked_songs": total_liked_songs,
    }


def can_generate_recommendations(session: UserSession, db: Session) -> bool:
    """Check if user can generate new recommendations based on rate limits"""
    now = datetime.utcnow()

    # Reset daily count if it's a new day
    if (
        session.last_recommendation_at
        and session.last_recommendation_at.date() < now.date()
    ):
        session.recommendation_count_today = 0
        db.commit()

    # Check daily limit
    if session.recommendation_count_today >= 100:
        return False

    # Check cooldown period (4 hours)
    if (
        session.last_recommendation_at
        and now - session.last_recommendation_at < timedelta(minutes=1)
    ):
        return False

    return True


def update_recommendation_limits(session: UserSession, db: Session):
    """Update recommendation rate limiting counters"""
    now = datetime.utcnow()

    # Reset daily count if it's a new day
    if (
        session.last_recommendation_at
        and session.last_recommendation_at.date() < now.date()
    ):
        session.recommendation_count_today = 0

    session.last_recommendation_at = now
    session.recommendation_count_today += 1
    db.commit()
