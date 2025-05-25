"""
Recommendation engine for generating music recommendations
"""

import random
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.models import User, Track, UserCluster, Recommendation, BillboardChart
from app.services.spotify_client import SpotifyClient
from app.services.data_analyzer import DataAnalyzer
from app.services.billboard_scraper import BillboardScraper

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Service for generating music recommendations"""

    def __init__(self):
        self.spotify_client = SpotifyClient()
        self.data_analyzer = DataAnalyzer()
        self.billboard_scraper = BillboardScraper()

    def generate_cluster_recommendations(
        self, access_token: str, user_id: int, limit: int, db: Session
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on user's music taste clusters"""
        try:
            # Get user's clusters
            clusters = (
                db.query(UserCluster).filter(UserCluster.user_id == user_id).all()
            )

            if not clusters:
                logger.warning(f"No clusters found for user {user_id}")
                return []

            # Get user's existing tracks to exclude from recommendations
            existing_tracks = db.query(Track).filter(Track.user_id == user_id).all()
            existing_track_ids = {track.spotify_id for track in existing_tracks}

            recommendations = []
            tracks_per_cluster = max(1, limit // len(clusters))

            for cluster in clusters:
                cluster_recs = self._generate_recommendations_for_cluster(
                    access_token, cluster, tracks_per_cluster, existing_track_ids, db
                )
                recommendations.extend(cluster_recs)

            # Shuffle and limit results
            random.shuffle(recommendations)
            recommendations = recommendations[:limit]

            # Store recommendations in database
            self._store_recommendations(user_id, recommendations, "cluster", db)

            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate cluster recommendations: {e}")
            return []

    def generate_nostalgia_recommendations(
        self, access_token: str, user_id: int, limit: int, db: Session
    ) -> List[Dict[str, Any]]:
        """Generate nostalgia recommendations based on formative years"""
        try:
            # Get user info
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.date_of_birth:
                logger.error(f"User {user_id} missing date of birth")
                return []

            # Calculate formative years
            formative_years = self.data_analyzer.calculate_formative_years(
                user.date_of_birth
            )

            # Get user's taste profile from clusters
            clusters = (
                db.query(UserCluster).filter(UserCluster.user_id == user_id).all()
            )
            if not clusters:
                logger.warning(f"No clusters found for user {user_id}")
                return []

            # Get Billboard data for formative years
            billboard_tracks = self._get_billboard_tracks_for_years(
                formative_years["years"], db
            )

            if not billboard_tracks:
                logger.warning(
                    f"No Billboard data found for years {formative_years['years']}"
                )
                return []

            # Get user's existing tracks to exclude
            existing_tracks = db.query(Track).filter(Track.user_id == user_id).all()
            existing_track_ids = {track.spotify_id for track in existing_tracks}

            # Filter Billboard tracks by similarity to user's taste
            similar_tracks = self._filter_by_taste_similarity(
                billboard_tracks, clusters, existing_track_ids
            )

            # Get Spotify data for similar tracks
            recommendations = self._enrich_with_spotify_data(
                access_token, similar_tracks[: limit * 2]  # Get more to filter
            )

            # Filter out tracks already in user's library
            recommendations = [
                rec
                for rec in recommendations
                if rec.get("spotify_id") not in existing_track_ids
            ]

            # Limit results
            recommendations = recommendations[:limit]

            # Store recommendations in database
            self._store_recommendations(user_id, recommendations, "nostalgia", db)

            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate nostalgia recommendations: {e}")
            return []

    def _generate_recommendations_for_cluster(
        self,
        access_token: str,
        cluster: UserCluster,
        limit: int,
        existing_track_ids: set,
        db: Session,
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for a specific cluster"""
        try:
            # Get sample tracks from this cluster for seeds
            cluster_tracks = (
                db.query(Track)
                .filter(
                    Track.user_id == cluster.user_id,
                    Track.cluster_id == cluster.cluster_id,
                )
                .limit(5)
                .all()
            )

            if not cluster_tracks:
                return []

            # Use cluster centroid as target features
            target_features = cluster.centroid_data

            # Get seed tracks and artists
            seed_tracks = [track.spotify_id for track in cluster_tracks[:3]]
            seed_artists = list(
                set(
                    [
                        track.artist_name.split(",")[0].strip()
                        for track in cluster_tracks
                    ]
                )
            )[:3]

            # Get recommendations from Spotify
            spotify_recs = self.spotify_client.get_recommendations(
                access_token=access_token,
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                target_features=target_features,
                limit=limit * 2,  # Get more to filter
            )

            # Filter and format recommendations
            recommendations = []
            for track in spotify_recs:
                if track["id"] not in existing_track_ids:
                    rec = {
                        "spotify_id": track["id"],
                        "name": track["name"],
                        "artist_name": ", ".join(
                            [artist["name"] for artist in track["artists"]]
                        ),
                        "album_name": track["album"]["name"],
                        "preview_url": track["preview_url"],
                        "external_url": track["external_urls"]["spotify"],
                        "image_url": (
                            track["album"]["images"][0]["url"]
                            if track["album"]["images"]
                            else None
                        ),
                        "source_cluster_id": cluster.cluster_id,
                        "confidence_score": self._calculate_confidence_score(
                            track, target_features
                        ),
                    }
                    recommendations.append(rec)

            return recommendations[:limit]

        except Exception as e:
            logger.error(
                f"Failed to generate recommendations for cluster {cluster.cluster_id}: {e}"
            )
            return []

    def _get_billboard_tracks_for_years(
        self, years: List[int], db: Session
    ) -> List[BillboardChart]:
        """Get Billboard tracks for specified years"""
        # Check if we have data for these years
        existing_data = (
            db.query(BillboardChart)
            .filter(
                BillboardChart.chart_date.between(
                    datetime(min(years), 1, 1), datetime(max(years), 12, 31)
                )
            )
            .all()
        )

        if len(existing_data) < 100:  # If we don't have enough data, scrape it
            logger.info(f"Scraping Billboard data for years {years}")
            self.billboard_scraper.scrape_years(years, db)

            # Re-query after scraping
            existing_data = (
                db.query(BillboardChart)
                .filter(
                    BillboardChart.chart_date.between(
                        datetime(min(years), 1, 1), datetime(max(years), 12, 31)
                    )
                )
                .all()
            )

        return existing_data

    def _filter_by_taste_similarity(
        self,
        billboard_tracks: List[BillboardChart],
        user_clusters: List[UserCluster],
        existing_track_ids: set,
    ) -> List[BillboardChart]:
        """Filter Billboard tracks by similarity to user's taste clusters"""
        if not user_clusters:
            return billboard_tracks

        # Calculate average user taste profile
        user_profile = {}
        total_tracks = sum(cluster.track_count for cluster in user_clusters)

        for feature in self.data_analyzer.audio_features:
            weighted_sum = sum(
                cluster.centroid_data.get(feature, 0.5) * cluster.track_count
                for cluster in user_clusters
                if feature in cluster.centroid_data
            )
            user_profile[feature] = (
                weighted_sum / total_tracks if total_tracks > 0 else 0.5
            )

        # Filter tracks with audio features similar to user profile
        similar_tracks = []
        for track in billboard_tracks:
            if (
                track.spotify_track_id
                and track.spotify_track_id not in existing_track_ids
                and self._is_similar_to_profile(track, user_profile)
            ):
                similar_tracks.append(track)

        # Sort by similarity score
        similar_tracks.sort(
            key=lambda t: self._calculate_similarity_score(t, user_profile),
            reverse=True,
        )

        return similar_tracks

    def _is_similar_to_profile(
        self, track: BillboardChart, user_profile: Dict[str, float]
    ) -> bool:
        """Check if a track is similar to user's taste profile"""
        if not all(
            getattr(track, feature) is not None
            for feature in ["energy", "valence", "danceability"]
        ):
            return False

        # Simple similarity check based on key features
        energy_diff = abs(
            getattr(track, "energy", 0.5) - user_profile.get("energy", 0.5)
        )
        valence_diff = abs(
            getattr(track, "valence", 0.5) - user_profile.get("valence", 0.5)
        )
        dance_diff = abs(
            getattr(track, "danceability", 0.5) - user_profile.get("danceability", 0.5)
        )

        # Track is similar if it's within reasonable bounds for key features
        return energy_diff < 0.4 and valence_diff < 0.4 and dance_diff < 0.4

    def _calculate_similarity_score(
        self, track: BillboardChart, user_profile: Dict[str, float]
    ) -> float:
        """Calculate similarity score between track and user profile"""
        score = 0.0
        feature_count = 0

        for feature in self.data_analyzer.audio_features:
            track_value = getattr(track, feature, None)
            profile_value = user_profile.get(feature)

            if track_value is not None and profile_value is not None:
                # Calculate inverse of absolute difference (higher score = more similar)
                diff = abs(track_value - profile_value)
                score += 1.0 - diff
                feature_count += 1

        return score / feature_count if feature_count > 0 else 0.0

    def _enrich_with_spotify_data(
        self, access_token: str, billboard_tracks: List[BillboardChart]
    ) -> List[Dict[str, Any]]:
        """Enrich Billboard tracks with Spotify data"""
        recommendations = []

        for track in billboard_tracks:
            if not track.spotify_track_id:
                # Try to find the track on Spotify
                query = f"{track.track_name} {track.artist_name}"
                search_results = self.spotify_client.search_tracks(
                    access_token, query, limit=1
                )

                if search_results:
                    spotify_track = search_results[0]
                    track.spotify_track_id = spotify_track["id"]
                else:
                    continue

            # Create recommendation object
            rec = {
                "spotify_id": track.spotify_track_id,
                "name": track.track_name,
                "artist_name": track.artist_name,
                "album_name": None,  # Will be filled from Spotify if needed
                "preview_url": None,
                "external_url": f"https://open.spotify.com/track/{track.spotify_track_id}",
                "image_url": None,
                "source_cluster_id": None,
                "confidence_score": 0.8,  # Base score for nostalgia tracks
                "chart_position": track.position,
                "chart_date": track.chart_date.isoformat(),
            }
            recommendations.append(rec)

        return recommendations

    def _calculate_confidence_score(
        self, spotify_track: Dict[str, Any], target_features: Dict[str, float]
    ) -> float:
        """Calculate confidence score for a recommendation"""
        # This is a simplified confidence calculation
        # In a real implementation, you might use audio features similarity
        popularity = spotify_track.get("popularity", 50)
        return min(1.0, popularity / 100.0 + 0.3)

    def _store_recommendations(
        self,
        user_id: int,
        recommendations: List[Dict[str, Any]],
        recommendation_type: str,
        db: Session,
    ):
        """Store recommendations in the database"""
        try:
            for rec in recommendations:
                recommendation = Recommendation(
                    user_id=user_id,
                    spotify_track_id=rec["spotify_id"],
                    track_name=rec["name"],
                    artist_name=rec["artist_name"],
                    album_name=rec.get("album_name"),
                    preview_url=rec.get("preview_url"),
                    external_url=rec.get("external_url"),
                    image_url=rec.get("image_url"),
                    recommendation_type=recommendation_type,
                    source_cluster_id=rec.get("source_cluster_id"),
                    confidence_score=rec.get("confidence_score", 0.5),
                )
                db.add(recommendation)

            db.commit()
            logger.info(
                f"Stored {len(recommendations)} {recommendation_type} recommendations for user {user_id}"
            )

        except Exception as e:
            logger.error(f"Failed to store recommendations: {e}")
            db.rollback()
