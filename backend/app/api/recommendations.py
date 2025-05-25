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
        # Check if user already has tracks analyzed
        existing_tracks = db.query(Track).filter(Track.user_id == user.id).count()

        if existing_tracks > 0:
            return {
                "message": "Library already analyzed",
                "track_count": existing_tracks,
                "status": "completed",
            }

        # Start background analysis
        background_tasks.add_task(
            analyze_library_background,
            session.access_token,
            user.id,
            request.track_limit,
            db,
        )

        return {
            "message": "Library analysis started",
            "status": "processing",
            "estimated_time": "2-5 minutes",
        }

    except Exception as e:
        logger.error(f"Failed to start library analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


async def analyze_library_background(
    access_token: str, user_id: int, track_limit: int, db: Session
):
    """Background task to analyze user's library"""
    try:
        # Fetch user's saved tracks
        logger.info(f"Fetching {track_limit} tracks for user {user_id}")
        saved_tracks = spotify_client.get_user_saved_tracks(
            access_token, limit=track_limit
        )

        if not saved_tracks:
            logger.warning(f"No tracks found for user {user_id}")
            return

        # Extract track IDs
        track_ids = [
            item["track"]["id"] for item in saved_tracks if item["track"]["id"]
        ]

        # Get audio features
        logger.info(f"Getting audio features for {len(track_ids)} tracks")
        audio_features = spotify_client.get_audio_features(access_token, track_ids)

        # Create feature mapping
        features_map = {f["id"]: f for f in audio_features if f}

        # Store tracks in database
        tracks_data = []
        for item in saved_tracks:
            track = item["track"]
            if not track["id"] or track["id"] not in features_map:
                continue

            features = features_map[track["id"]]

            track_data = Track(
                spotify_id=track["id"],
                user_id=user_id,
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
                # Audio features
                acousticness=features["acousticness"],
                danceability=features["danceability"],
                energy=features["energy"],
                instrumentalness=features["instrumentalness"],
                liveness=features["liveness"],
                loudness=features["loudness"],
                speechiness=features["speechiness"],
                tempo=features["tempo"],
                valence=features["valence"],
                key=features["key"],
                mode=features["mode"],
                time_signature=features["time_signature"],
            )
            tracks_data.append(track_data)

        # Bulk insert tracks
        db.bulk_save_objects(tracks_data)
        db.commit()

        logger.info(f"Stored {len(tracks_data)} tracks for user {user_id}")

        # Perform clustering
        logger.info(f"Starting clustering analysis for user {user_id}")
        clusters = data_analyzer.perform_clustering(user_id, db)

        logger.info(
            f"Clustering completed for user {user_id}: {len(clusters)} clusters created"
        )

    except Exception as e:
        logger.error(f"Background analysis failed for user {user_id}: {e}")
        db.rollback()


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
        else:
            raise HTTPException(status_code=400, detail="Invalid recommendation type")

        # Update rate limiting
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
    if session.recommendation_count_today >= 4:
        return False

    # Check cooldown period (4 hours)
    if (
        session.last_recommendation_at
        and now - session.last_recommendation_at < timedelta(hours=4)
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
