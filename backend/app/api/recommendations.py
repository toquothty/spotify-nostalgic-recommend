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


@router.get("/debug-audio-features")
async def debug_audio_features(session_id: str, db: Session = Depends(get_db)):
    """Debug endpoint to test audio features specifically"""
    try:
        session = get_current_session(session_id, db)
        user = db.query(User).filter(User.id == session.user_id).first()

        # Test basic API call first
        try:
            total_tracks = spotify_client.get_user_saved_tracks_count(
                session.access_token
            )
            logger.info(f"DEBUG: Basic API works, got {total_tracks} tracks")
        except Exception as e:
            return {"status": "error", "step": "basic_api", "error": str(e)}

        # Get a few tracks
        try:
            saved_tracks = spotify_client.get_user_saved_tracks(
                session.access_token, limit=3
            )
            track_ids = [
                item["track"]["id"] for item in saved_tracks if item["track"]["id"]
            ]
            logger.info(f"DEBUG: Got {len(track_ids)} track IDs: {track_ids}")
        except Exception as e:
            return {"status": "error", "step": "get_tracks", "error": str(e)}

        # Test audio features with just one track
        if track_ids:
            try:
                single_track_id = track_ids[0]
                logger.info(
                    f"DEBUG: Testing audio features for single track: {single_track_id}"
                )

                # Try direct spotipy call
                sp = spotify_client.get_spotify_client(session.access_token)
                features = sp.audio_features([single_track_id])

                logger.info(f"DEBUG: Audio features result: {features}")

                return {
                    "status": "success",
                    "track_id": single_track_id,
                    "features": features,
                    "total_tracks": total_tracks,
                }

            except Exception as e:
                logger.error(f"DEBUG: Audio features failed: {e}")
                return {
                    "status": "error",
                    "step": "audio_features",
                    "error": str(e),
                    "track_id": single_track_id,
                }

        return {"status": "error", "step": "no_tracks", "error": "No track IDs found"}

    except Exception as e:
        logger.error(f"DEBUG: General error: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/debug-token")
async def debug_token(session_id: str, db: Session = Depends(get_db)):
    """Debug endpoint to test token refresh"""
    try:
        session = get_current_session(session_id, db)
        user = db.query(User).filter(User.id == session.user_id).first()

        logger.info(f"DEBUG: Token expires at: {session.token_expires_at}")
        logger.info(f"DEBUG: Current time: {datetime.utcnow()}")
        logger.info(
            f"DEBUG: Token expired: {datetime.utcnow() >= session.token_expires_at}"
        )

        # Test a simple Spotify API call
        try:
            total_tracks = spotify_client.get_user_saved_tracks_count(
                session.access_token
            )
            logger.info(f"DEBUG: Successfully got track count: {total_tracks}")
            return {
                "status": "success",
                "total_tracks": total_tracks,
                "token_valid": True,
            }
        except Exception as e:
            logger.error(f"DEBUG: Spotify API failed: {e}")
            return {"status": "error", "error": str(e), "token_valid": False}

    except Exception as e:
        logger.error(f"DEBUG: General error: {e}")
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

        # Check if user already has tracks analyzed
        existing_tracks = db.query(Track).filter(Track.user_id == user.id).count()

        if existing_tracks > 0:
            return {
                "message": "Library already analyzed",
                "track_count": existing_tracks,
                "status": "completed",
            }

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

        # Complete analysis
        progress_tracker.complete_analysis(user.id, tracks_stored, 1, db)

        return {
            "message": "Analysis completed successfully (using workaround for audio features)",
            "status": "completed",
            "tracks_analyzed": tracks_stored,
            "note": "Audio features API is currently unavailable. Using default values for now.",
        }

    except Exception as e:
        logger.error(f"Failed to start library analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


async def analyze_library_background(session_id: str, user_id: int, track_limit: int):
    """Background task to analyze user's library with automatic token refresh"""
    from app.database import SessionLocal

    db = SessionLocal()
    try:

        def get_fresh_token():
            """Get a fresh access token with automatic refresh"""
            session = (
                db.query(UserSession)
                .filter(UserSession.session_id == session_id)
                .first()
            )
            if not session:
                raise Exception("Session not found")

            logger.info(
                f"Token expires at: {session.token_expires_at}, current time: {datetime.utcnow()}"
            )

            # Check if token needs refresh
            if datetime.utcnow() >= session.token_expires_at:
                logger.info(f"Token expired, refreshing for user {user_id}")
                try:
                    token_data = spotify_client.refresh_access_token(
                        session.refresh_token
                    )
                    session.access_token = token_data["access_token"]
                    session.refresh_token = token_data["refresh_token"]
                    session.token_expires_at = token_data["expires_at"]
                    db.commit()
                    logger.info(f"Token refreshed successfully for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to refresh token for user {user_id}: {e}")
                    raise Exception(f"Failed to refresh token: {e}")
            else:
                logger.info(f"Token still valid for user {user_id}")

            return session.access_token

        # Update progress: Starting
        progress_tracker.update_progress(
            user_id=user_id,
            status="fetching_tracks",
            current_step="Fetching your liked songs from Spotify...",
            tracks_processed=0,
            progress_percentage=5,
            db=db,
        )

        # Get fresh token and fetch user's saved tracks
        access_token = get_fresh_token()
        logger.info(f"Fetching {track_limit} tracks for user {user_id}")
        saved_tracks = spotify_client.get_user_saved_tracks(
            access_token, limit=track_limit
        )

        if not saved_tracks:
            logger.warning(f"No tracks found for user {user_id}")
            progress_tracker.set_error(user_id, "No tracks found in your library", db)
            return

        # Update progress: Tracks fetched
        progress_tracker.update_progress(
            user_id=user_id,
            status="getting_features",
            current_step=f"Analyzing audio features for {len(saved_tracks)} tracks...",
            tracks_processed=0,
            progress_percentage=20,
            db=db,
        )

        # Extract track IDs
        track_ids = [
            item["track"]["id"] for item in saved_tracks if item["track"]["id"]
        ]

        # Get fresh token and audio features
        access_token = get_fresh_token()
        logger.info(f"Getting audio features for {len(track_ids)} tracks")
        audio_features = spotify_client.get_audio_features(access_token, track_ids)

        # Update progress: Features obtained
        progress_tracker.update_progress(
            user_id=user_id,
            status="getting_features",
            current_step="Processing track data and storing in database...",
            tracks_processed=len(track_ids),
            progress_percentage=60,
            db=db,
        )

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

        # Update progress: Starting clustering
        progress_tracker.update_progress(
            user_id=user_id,
            status="clustering",
            current_step="Creating music taste clusters using AI...",
            tracks_processed=len(tracks_data),
            progress_percentage=80,
            db=db,
        )

        # Perform clustering
        logger.info(f"Starting clustering analysis for user {user_id}")
        clusters = data_analyzer.perform_clustering(user_id, db)

        logger.info(
            f"Clustering completed for user {user_id}: {len(clusters)} clusters created"
        )

        # Complete analysis
        progress_tracker.complete_analysis(
            user_id=user_id,
            final_track_count=len(tracks_data),
            cluster_count=len(clusters),
            db=db,
        )

    except Exception as e:
        logger.error(f"Background analysis failed for user {user_id}: {e}")
        progress_tracker.set_error(user_id, str(e), db)
        db.rollback()
    finally:
        db.close()


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
