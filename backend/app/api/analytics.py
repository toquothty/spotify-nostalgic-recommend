"""
Analytics API endpoints for music taste analysis
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from app.database import get_db
from app.models import User, Track, UserCluster, Recommendation
from app.services.data_analyzer import DataAnalyzer
from app.api.auth import get_current_session
from app.schemas import AnalyticsResponse, ClusterResponse, TasteEvolutionResponse

router = APIRouter()
data_analyzer = DataAnalyzer()

logger = logging.getLogger(__name__)


@router.get("/overview")
async def get_analytics_overview(session_id: str, db: Session = Depends(get_db)):
    """Get comprehensive analytics overview for user"""
    session = get_current_session(session_id, db)
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Get basic stats
        total_tracks = db.query(Track).filter(Track.user_id == user.id).count()

        if total_tracks == 0:
            return {
                "total_tracks": 0,
                "clusters": [],
                "top_genres": [],
                "audio_features_summary": {},
                "formative_years": None,
                "message": "No tracks analyzed yet",
            }

        # Get clusters
        clusters = db.query(UserCluster).filter(UserCluster.user_id == user.id).all()
        cluster_responses = [ClusterResponse.from_orm(cluster) for cluster in clusters]

        # Get cluster characteristics
        cluster_characteristics = data_analyzer.get_cluster_characteristics(user.id, db)

        # Enhance cluster responses with characteristics
        for cluster_resp in cluster_responses:
            if cluster_resp.cluster_id in cluster_characteristics:
                cluster_resp.characteristics = cluster_characteristics[
                    cluster_resp.cluster_id
                ]

        # Calculate audio features summary
        audio_features_summary = _calculate_audio_features_summary(user.id, db)

        # Get top artists (simplified genre analysis)
        top_artists = _get_top_artists(user.id, db)

        # Calculate formative years if DOB available
        formative_years = None
        if user.date_of_birth:
            formative_years = data_analyzer.calculate_formative_years(
                user.date_of_birth
            )

        return {
            "total_tracks": total_tracks,
            "clusters": cluster_responses,
            "top_genres": top_artists,  # Using artists as proxy for genres
            "audio_features_summary": audio_features_summary,
            "formative_years": formative_years,
            "cluster_characteristics": cluster_characteristics,
        }

    except Exception as e:
        logger.error(f"Failed to get analytics overview: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")


@router.get("/taste-evolution")
async def get_taste_evolution(session_id: str, db: Session = Depends(get_db)):
    """Get user's music taste evolution over time"""
    session = get_current_session(session_id, db)
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        evolution_data = data_analyzer.get_taste_evolution(user.id, db)

        # Convert to response format
        evolution_responses = []
        for period_data in evolution_data:
            evolution_responses.append(
                TasteEvolutionResponse(
                    period=period_data["period"],
                    track_count=period_data["track_count"],
                    avg_features=period_data["avg_features"],
                    top_genres=period_data["top_artists"],  # Using artists as proxy
                    date_range=period_data["date_range"],
                )
            )

        return {
            "evolution": evolution_responses,
            "total_periods": len(evolution_responses),
        }

    except Exception as e:
        logger.error(f"Failed to get taste evolution: {e}")
        raise HTTPException(
            status_code=500, detail=f"Taste evolution analysis failed: {str(e)}"
        )


@router.get("/clusters/{cluster_id}")
async def get_cluster_details(
    cluster_id: int, session_id: str, db: Session = Depends(get_db)
):
    """Get detailed information about a specific cluster"""
    session = get_current_session(session_id, db)

    # Get cluster
    cluster = (
        db.query(UserCluster)
        .filter(
            UserCluster.user_id == session.user_id, UserCluster.cluster_id == cluster_id
        )
        .first()
    )

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        # Get tracks in this cluster
        tracks = (
            db.query(Track)
            .filter(Track.user_id == session.user_id, Track.cluster_id == cluster_id)
            .all()
        )

        # Get cluster characteristics
        characteristics = data_analyzer.get_cluster_characteristics(session.user_id, db)
        cluster_char = characteristics.get(cluster_id, {})

        # Get recommendations generated from this cluster
        recommendations = (
            db.query(Recommendation)
            .filter(
                Recommendation.user_id == session.user_id,
                Recommendation.source_cluster_id == cluster_id,
            )
            .limit(10)
            .all()
        )

        return {
            "cluster": ClusterResponse.from_orm(cluster),
            "characteristics": cluster_char,
            "tracks": [
                {
                    "id": track.id,
                    "name": track.name,
                    "artist_name": track.artist_name,
                    "album_name": track.album_name,
                    "spotify_id": track.spotify_id,
                    "image_url": track.image_url,
                    "added_at": track.added_at.isoformat() if track.added_at else None,
                }
                for track in tracks
            ],
            "recommendations": [
                {
                    "id": rec.id,
                    "track_name": rec.track_name,
                    "artist_name": rec.artist_name,
                    "spotify_track_id": rec.spotify_track_id,
                    "confidence_score": rec.confidence_score,
                    "user_liked": rec.user_liked,
                }
                for rec in recommendations
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get cluster details: {e}")
        raise HTTPException(
            status_code=500, detail=f"Cluster analysis failed: {str(e)}"
        )


@router.get("/recommendations-stats")
async def get_recommendations_stats(session_id: str, db: Session = Depends(get_db)):
    """Get statistics about user's recommendations"""
    session = get_current_session(session_id, db)

    try:
        # Get all recommendations for user
        recommendations = (
            db.query(Recommendation)
            .filter(Recommendation.user_id == session.user_id)
            .all()
        )

        if not recommendations:
            return {
                "total_recommendations": 0,
                "liked_count": 0,
                "disliked_count": 0,
                "already_knew_count": 0,
                "pending_feedback": 0,
                "by_type": {},
                "by_cluster": {},
            }

        # Calculate stats
        total_recommendations = len(recommendations)
        liked_count = sum(1 for r in recommendations if r.user_liked is True)
        disliked_count = sum(1 for r in recommendations if r.user_liked is False)
        already_knew_count = sum(
            1 for r in recommendations if r.user_already_knew is True
        )
        pending_feedback = sum(
            1
            for r in recommendations
            if r.user_liked is None and r.user_already_knew is None
        )

        # Group by recommendation type
        by_type = {}
        for rec in recommendations:
            rec_type = rec.recommendation_type
            if rec_type not in by_type:
                by_type[rec_type] = {"count": 0, "liked": 0}
            by_type[rec_type]["count"] += 1
            if rec.user_liked is True:
                by_type[rec_type]["liked"] += 1

        # Group by source cluster
        by_cluster = {}
        for rec in recommendations:
            if rec.source_cluster_id is not None:
                cluster_id = rec.source_cluster_id
                if cluster_id not in by_cluster:
                    by_cluster[cluster_id] = {"count": 0, "liked": 0}
                by_cluster[cluster_id]["count"] += 1
                if rec.user_liked is True:
                    by_cluster[cluster_id]["liked"] += 1

        return {
            "total_recommendations": total_recommendations,
            "liked_count": liked_count,
            "disliked_count": disliked_count,
            "already_knew_count": already_knew_count,
            "pending_feedback": pending_feedback,
            "like_rate": (
                liked_count / total_recommendations if total_recommendations > 0 else 0
            ),
            "by_type": by_type,
            "by_cluster": by_cluster,
        }

    except Exception as e:
        logger.error(f"Failed to get recommendation stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Recommendation stats failed: {str(e)}"
        )


@router.get("/audio-features-distribution")
async def get_audio_features_distribution(
    session_id: str, db: Session = Depends(get_db)
):
    """Get distribution of audio features across user's library"""
    session = get_current_session(session_id, db)

    try:
        tracks = db.query(Track).filter(Track.user_id == session.user_id).all()

        if not tracks:
            return {"message": "No tracks found"}

        # Calculate distributions for each audio feature
        features = [
            "acousticness",
            "danceability",
            "energy",
            "instrumentalness",
            "liveness",
            "loudness",
            "speechiness",
            "tempo",
            "valence",
        ]

        distributions = {}

        for feature in features:
            values = [
                getattr(track, feature)
                for track in tracks
                if getattr(track, feature) is not None
            ]

            if values:
                # Create histogram bins
                if feature == "tempo":
                    bins = [0, 80, 100, 120, 140, 160, 200, 300]
                elif feature == "loudness":
                    bins = [-60, -30, -20, -10, -5, 0, 5]
                else:
                    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]

                histogram = _create_histogram(values, bins)

                distributions[feature] = {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "histogram": histogram,
                    "total_tracks": len(values),
                }

        return {"distributions": distributions, "total_tracks_analyzed": len(tracks)}

    except Exception as e:
        logger.error(f"Failed to get audio features distribution: {e}")
        raise HTTPException(
            status_code=500, detail=f"Audio features analysis failed: {str(e)}"
        )


def _calculate_audio_features_summary(user_id: int, db: Session) -> Dict[str, float]:
    """Calculate summary statistics for user's audio features"""
    tracks = db.query(Track).filter(Track.user_id == user_id).all()

    if not tracks:
        return {}

    features = [
        "acousticness",
        "danceability",
        "energy",
        "instrumentalness",
        "liveness",
        "loudness",
        "speechiness",
        "tempo",
        "valence",
    ]

    summary = {}
    for feature in features:
        values = [
            getattr(track, feature)
            for track in tracks
            if getattr(track, feature) is not None
        ]
        if values:
            summary[feature] = sum(values) / len(values)

    return summary


def _get_top_artists(
    user_id: int, db: Session, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get top artists for user (as proxy for genres)"""
    tracks = db.query(Track).filter(Track.user_id == user_id).all()

    if not tracks:
        return []

    # Count artist occurrences
    artist_counts = {}
    for track in tracks:
        artist = track.artist_name.split(",")[
            0
        ].strip()  # Take first artist if multiple
        artist_counts[artist] = artist_counts.get(artist, 0) + 1

    # Sort by count and return top artists
    top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[
        :limit
    ]

    return [{"name": artist, "count": count} for artist, count in top_artists]


def _create_histogram(values: List[float], bins: List[float]) -> List[Dict[str, Any]]:
    """Create histogram from values and bins"""
    histogram = []

    for i in range(len(bins) - 1):
        bin_start = bins[i]
        bin_end = bins[i + 1]

        count = sum(1 for value in values if bin_start <= value < bin_end)

        # Handle the last bin to include the maximum value
        if i == len(bins) - 2:
            count = sum(1 for value in values if bin_start <= value <= bin_end)

        histogram.append(
            {
                "bin_start": bin_start,
                "bin_end": bin_end,
                "count": count,
                "percentage": count / len(values) * 100 if values else 0,
            }
        )

    return histogram
