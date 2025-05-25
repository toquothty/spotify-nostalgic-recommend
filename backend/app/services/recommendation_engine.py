"""
Recommendation engine for generating music recommendations
Using metadata-based approach due to audio features API deprecation
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
    """Generate recommendations using metadata-based approach"""

    def __init__(self):
        self.spotify_client = SpotifyClient()

    def generate_cluster_recommendations(
        self, access_token: str, user_id: int, limit: int, db: Session
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on artist and genre similarity"""
        try:
            # Get user's tracks
            user_tracks = db.query(Track).filter(Track.user_id == user_id).all()

            if not user_tracks:
                logger.warning(f"No tracks found for user {user_id}")
                return []

            # Extract unique artists from user's library
            user_artists = list(set([track.artist_name for track in user_tracks]))
            logger.info(f"User has {len(user_artists)} unique artists")

            # Get recommendations based on top artists
            recommendations = []
            artists_to_use = min(5, len(user_artists))  # Use up to 5 artists
            selected_artists = random.sample(user_artists, artists_to_use)

            for artist in selected_artists:
                # Search for the artist to get their ID
                artist_results = self.spotify_client.search_tracks(
                    access_token, f"artist:{artist}", limit=1
                )

                if artist_results and artist_results[0].get("artists"):
                    artist_id = artist_results[0]["artists"][0]["id"]

                    # Get related artists
                    related = self._get_related_artists(access_token, artist_id)

                    for related_artist in related[
                        :2
                    ]:  # Get 2 related artists per seed artist
                        # Get top tracks for related artist
                        tracks = self._get_artist_top_tracks(
                            access_token, related_artist["id"]
                        )
                        recommendations.extend(
                            tracks[:2]
                        )  # Add 2 tracks per related artist

            # Remove duplicates and already liked songs
            user_track_ids = [track.spotify_id for track in user_tracks]
            unique_recommendations = []
            seen_ids = set()

            for rec in recommendations:
                if rec["id"] not in user_track_ids and rec["id"] not in seen_ids:
                    seen_ids.add(rec["id"])
                    unique_recommendations.append(rec)

            # Limit to requested number
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

            # Get user's favorite genres from their tracks
            user_tracks = db.query(Track).filter(Track.user_id == user_id).all()
            user_artists = list(set([track.artist_name for track in user_tracks]))

            # Search for popular songs from formative years
            recommendations = []

            for year in range(formative_start, formative_end + 1):
                # Search for popular songs from that year
                search_queries = [
                    f"year:{year}",
                    f"year:{year} genre:pop",
                    f"year:{year} genre:rock",
                    f"year:{year} genre:hip-hop",
                ]

                for query in search_queries:
                    results = self.spotify_client.search_tracks(
                        access_token, query, limit=5
                    )

                    for track in results:
                        # Filter by popularity to get actual hits from that era
                        if track.get("popularity", 0) > 50:
                            track["nostalgia_year"] = year
                            track["user_age"] = year - birth_year
                            recommendations.append(track)

            # Remove duplicates and already liked songs
            user_track_ids = [track.spotify_id for track in user_tracks]
            unique_recommendations = []
            seen_ids = set()

            for rec in recommendations:
                if rec["id"] not in user_track_ids and rec["id"] not in seen_ids:
                    seen_ids.add(rec["id"])
                    unique_recommendations.append(rec)

            # Sort by popularity and limit
            unique_recommendations.sort(
                key=lambda x: x.get("popularity", 0), reverse=True
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
                    # Get full track info from Spotify
                    track_info = self._get_track_info(access_token, track.spotify_id)
                    if track_info:
                        track_info["added_at"] = track.added_at.isoformat()
                        track_info["days_ago"] = (
                            datetime.utcnow() - track.added_at
                        ).days
                        forgotten_favorites.append(track_info)

            return forgotten_favorites

        except Exception as e:
            logger.error(f"Failed to get forgotten favorites: {e}")
            return []

    def _get_related_artists(
        self, access_token: str, artist_id: str
    ) -> List[Dict[str, Any]]:
        """Get related artists from Spotify"""
        try:
            sp = self.spotify_client.get_spotify_client(access_token)
            result = sp.artist_related_artists(artist_id)
            return result.get("artists", [])
        except Exception as e:
            logger.error(f"Failed to get related artists: {e}")
            return []

    def _get_artist_top_tracks(
        self, access_token: str, artist_id: str
    ) -> List[Dict[str, Any]]:
        """Get artist's top tracks"""
        try:
            sp = self.spotify_client.get_spotify_client(access_token)
            result = sp.artist_top_tracks(artist_id, country="US")
            return result.get("tracks", [])
        except Exception as e:
            logger.error(f"Failed to get artist top tracks: {e}")
            return []

    def _get_track_info(
        self, access_token: str, track_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get track information from Spotify"""
        try:
            sp = self.spotify_client.get_spotify_client(access_token)
            return sp.track(track_id)
        except Exception as e:
            logger.error(f"Failed to get track info: {e}")
            return None

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
                    artist_name=", ".join([a["name"] for a in track["artists"]]),
                    album_name=track["album"]["name"],
                    preview_url=track.get("preview_url"),
                    external_url=track["external_urls"].get("spotify"),
                    image_url=(
                        track["album"]["images"][0]["url"]
                        if track["album"]["images"]
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
