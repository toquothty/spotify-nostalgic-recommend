"""
Recommendation engine for generating music recommendations
Using only non-deprecated Spotify APIs
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import logging

from app.models import User, Track, UserCluster, Recommendation
from app.services.spotify_client import SpotifyClient

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Generate recommendations using only available Spotify APIs"""

    def __init__(self):
        self.spotify_client = SpotifyClient()

    def generate_cluster_recommendations(
        self, access_token: str, user_id: int, limit: int, db: Session
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on user's music taste using search API"""
        try:
            # Get user's tracks
            user_tracks = db.query(Track).filter(Track.user_id == user_id).all()

            if not user_tracks:
                logger.warning(f"No tracks found for user {user_id}")
                return []

            # Extract unique artists and analyze patterns
            artist_counts = {}
            for track in user_tracks:
                artist = track.artist_name
                artist_counts[artist] = artist_counts.get(artist, 0) + 1

            # Get top artists
            top_artists = sorted(
                artist_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]
            logger.info(f"User's top artists: {[a[0] for a in top_artists]}")

            # Generate recommendations by searching for similar music
            recommendations = []
            user_track_ids = [track.spotify_id for track in user_tracks]

            for artist_name, _ in top_artists:
                # Search for tracks by the same artist that user doesn't have
                search_query = f'artist:"{artist_name}"'
                search_results = self.spotify_client.search_tracks(
                    access_token, search_query, limit=50
                )

                for track in search_results:
                    if track["id"] not in user_track_ids:
                        recommendations.append(track)

            # Also search for tracks from similar time periods
            if user_tracks:
                # Get a sample of release years
                sample_tracks = random.sample(user_tracks, min(5, len(user_tracks)))
                for track in sample_tracks:
                    if track.release_date:
                        year = track.release_date[:4]
                        genre_searches = [
                            f"year:{year}",
                            f"year:{int(year)-1}-{int(year)+1}",
                        ]

                        for search in genre_searches:
                            results = self.spotify_client.search_tracks(
                                access_token, search, limit=10
                            )
                            for result in results:
                                if (
                                    result["id"] not in user_track_ids
                                    and result.get("popularity", 0) > 40
                                ):
                                    recommendations.append(result)

            # Remove duplicates
            seen_ids = set()
            unique_recommendations = []
            for rec in recommendations:
                if rec["id"] not in seen_ids:
                    seen_ids.add(rec["id"])
                    unique_recommendations.append(rec)

            # Sort by popularity and limit
            unique_recommendations.sort(
                key=lambda x: x.get("popularity", 0), reverse=True
            )
            final_recommendations = unique_recommendations[:limit]

            # Store recommendations in database
            for track in final_recommendations:
                self._store_recommendation(user_id, track, "cluster", db)

            logger.info(
                f"Generated {len(final_recommendations)} recommendations for user {user_id}"
            )
            return final_recommendations

        except Exception as e:
            logger.error(f"Failed to generate cluster recommendations: {e}")
            return []

    def generate_nostalgia_recommendations(
        self, access_token: str, user_id: int, limit: int, db: Session
    ) -> List[Dict[str, Any]]:
        """Generate nostalgic recommendations from user's formative years"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.date_of_birth:
                logger.warning(f"User {user_id} has no date of birth set")
                return []

            # Calculate formative years (ages 12-18)
            birth_year = user.date_of_birth.year
            formative_start = birth_year + 12
            formative_end = birth_year + 18

            logger.info(f"User's formative years: {formative_start}-{formative_end}")

            # Get user's tracks to exclude
            user_tracks = db.query(Track).filter(Track.user_id == user_id).all()
            user_track_ids = [track.spotify_id for track in user_tracks]

            # Search for popular songs from formative years
            recommendations = []

            for year in range(formative_start, formative_end + 1):
                # Search for popular songs from that year
                search_queries = [
                    f"year:{year}",
                    f"year:{year} tag:hipster",  # Less mainstream tracks
                ]

                for query in search_queries:
                    results = self.spotify_client.search_tracks(
                        access_token, query, limit=20
                    )

                    for track in results:
                        # Filter by popularity to get actual hits from that era
                        if (
                            track.get("popularity", 0) > 30
                            and track["id"] not in user_track_ids
                        ):
                            track["nostalgia_year"] = year
                            track["user_age"] = year - birth_year
                            recommendations.append(track)

            # Remove duplicates
            seen_ids = set()
            unique_recommendations = []
            for rec in recommendations:
                if rec["id"] not in seen_ids:
                    seen_ids.add(rec["id"])
                    unique_recommendations.append(rec)

            # Sort by a mix of year and popularity
            unique_recommendations.sort(
                key=lambda x: (x.get("nostalgia_year", 0), x.get("popularity", 0)),
                reverse=True,
            )
            final_recommendations = unique_recommendations[:limit]

            # Store recommendations in database
            for track in final_recommendations:
                self._store_recommendation(user_id, track, "nostalgia", db)

            logger.info(
                f"Generated {len(final_recommendations)} nostalgia recommendations for user {user_id}"
            )
            return final_recommendations

        except Exception as e:
            logger.error(f"Failed to generate nostalgia recommendations: {e}")
            return []

    def get_forgotten_favorites(
        self, access_token: str, user_id: int, limit: int, db: Session
    ) -> List[Dict[str, Any]]:
        """Find old liked songs that user might have forgotten about"""
        try:
            # Get user's tracks sorted by when they were added
            user_tracks = (
                db.query(Track)
                .filter(Track.user_id == user_id)
                .order_by(Track.added_at.asc())
                .all()
            )

            if not user_tracks:
                return []

            # Get tracks added more than 6 months ago
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            old_tracks = [
                track for track in user_tracks if track.added_at < six_months_ago
            ]

            # Randomly select some old favorites
            forgotten_favorites = []
            if old_tracks:
                sample_size = min(limit, len(old_tracks))
                selected_tracks = random.sample(old_tracks, sample_size)

                for track in selected_tracks:
                    # Create track info from our database
                    track_info = {
                        "id": track.spotify_id,
                        "name": track.name,
                        "artists": [{"name": track.artist_name}],
                        "album": {
                            "name": track.album_name,
                            "images": (
                                [{"url": track.image_url}] if track.image_url else []
                            ),
                        },
                        "external_urls": {"spotify": track.external_url},
                        "preview_url": track.preview_url,
                        "popularity": track.popularity,
                        "added_at": track.added_at.isoformat(),
                        "days_ago": (datetime.utcnow() - track.added_at).days,
                    }
                    forgotten_favorites.append(track_info)

            return forgotten_favorites

        except Exception as e:
            logger.error(f"Failed to get forgotten favorites: {e}")
            return []

    def _store_recommendation(
        self, user_id: int, track: Dict[str, Any], rec_type: str, db: Session
    ):
        """Store recommendation in database"""
        try:
            # Check if recommendation already exists
            existing = (
                db.query(Recommendation)
                .filter(
                    Recommendation.user_id == user_id,
                    Recommendation.spotify_track_id == track["id"],
                )
                .first()
            )

            if not existing:
                recommendation = Recommendation(
                    user_id=user_id,
                    spotify_track_id=track["id"],
                    track_name=track["name"],
                    artist_name=", ".join(
                        [a["name"] for a in track.get("artists", [])]
                    ),
                    album_name=track.get("album", {}).get("name", "Unknown Album"),
                    preview_url=track.get("preview_url"),
                    external_url=track.get("external_urls", {}).get("spotify"),
                    image_url=(
                        track.get("album", {}).get("images", [{}])[0].get("url")
                        if track.get("album", {}).get("images")
                        else None
                    ),
                    recommendation_type=rec_type,
                    score=track.get("popularity", 50) / 100.0,
                )
                db.add(recommendation)
                db.commit()

        except Exception as e:
            logger.error(f"Failed to store recommendation: {e}")
            db.rollback()
