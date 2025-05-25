"""
Data analysis service for clustering user's music taste
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from app.models import Track, UserCluster
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """Service for analyzing user's music data and performing clustering"""

    def __init__(self):
        self.audio_features = [
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
        self.scaler = StandardScaler()

    def perform_clustering(
        self, user_id: int, db: Session, n_clusters: int = 10
    ) -> List[UserCluster]:
        """Perform K-means clustering on user's tracks"""
        try:
            # Get user's tracks with audio features
            tracks = db.query(Track).filter(Track.user_id == user_id).all()

            if len(tracks) < n_clusters:
                logger.warning(
                    f"User {user_id} has fewer tracks ({len(tracks)}) than clusters ({n_clusters})"
                )
                n_clusters = max(2, len(tracks) // 2)

            # Prepare data for clustering
            features_data = []
            track_ids = []

            for track in tracks:
                if all(
                    getattr(track, feature) is not None
                    for feature in self.audio_features
                ):
                    features_data.append(
                        [getattr(track, feature) for feature in self.audio_features]
                    )
                    track_ids.append(track.id)

            if len(features_data) < n_clusters:
                logger.error(
                    f"Not enough valid tracks for clustering: {len(features_data)}"
                )
                return []

            # Convert to DataFrame for easier handling
            df = pd.DataFrame(features_data, columns=self.audio_features)

            # Normalize features
            normalized_features = self.scaler.fit_transform(df)

            # Perform K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(normalized_features)

            # Calculate silhouette score for quality assessment
            silhouette_avg = silhouette_score(normalized_features, cluster_labels)
            logger.info(
                f"Clustering silhouette score for user {user_id}: {silhouette_avg:.3f}"
            )

            # Update tracks with cluster assignments
            for i, track_id in enumerate(track_ids):
                track = db.query(Track).filter(Track.id == track_id).first()
                if track:
                    track.cluster_id = int(cluster_labels[i])

            # Create cluster centroids and store them
            clusters = []
            for cluster_id in range(n_clusters):
                cluster_mask = cluster_labels == cluster_id
                if np.any(cluster_mask):
                    # Calculate centroid in original feature space
                    cluster_features = df[cluster_mask]
                    centroid = cluster_features.mean().to_dict()

                    # Count tracks in this cluster
                    track_count = np.sum(cluster_mask)

                    # Create UserCluster record
                    user_cluster = UserCluster(
                        user_id=user_id,
                        cluster_id=cluster_id,
                        centroid_data=centroid,
                        track_count=track_count,
                    )

                    db.add(user_cluster)
                    clusters.append(user_cluster)

            db.commit()
            logger.info(f"Created {len(clusters)} clusters for user {user_id}")

            return clusters

        except Exception as e:
            logger.error(f"Clustering failed for user {user_id}: {e}")
            db.rollback()
            return []

    def get_cluster_characteristics(
        self, user_id: int, db: Session
    ) -> Dict[int, Dict[str, Any]]:
        """Get characteristics of each cluster for a user"""
        clusters = db.query(UserCluster).filter(UserCluster.user_id == user_id).all()

        characteristics = {}
        for cluster in clusters:
            # Get tracks in this cluster
            tracks = (
                db.query(Track)
                .filter(
                    Track.user_id == user_id, Track.cluster_id == cluster.cluster_id
                )
                .all()
            )

            if not tracks:
                continue

            # Calculate cluster characteristics
            characteristics[cluster.cluster_id] = {
                "centroid": cluster.centroid_data,
                "track_count": cluster.track_count,
                "sample_tracks": [
                    {
                        "name": track.name,
                        "artist": track.artist_name,
                        "spotify_id": track.spotify_id,
                    }
                    for track in tracks[:5]  # Sample tracks
                ],
                "dominant_features": self._get_dominant_features(cluster.centroid_data),
                "description": self._generate_cluster_description(
                    cluster.centroid_data
                ),
            }

        return characteristics

    def _get_dominant_features(self, centroid: Dict[str, float]) -> List[str]:
        """Identify the most prominent features in a cluster"""
        # Define thresholds for high/low values
        thresholds = {
            "acousticness": 0.7,
            "danceability": 0.7,
            "energy": 0.7,
            "instrumentalness": 0.5,
            "liveness": 0.3,
            "loudness": -5.0,  # dB, higher is louder
            "speechiness": 0.3,
            "tempo": 120.0,
            "valence": 0.7,
        }

        dominant = []
        for feature, value in centroid.items():
            if feature in thresholds:
                threshold = thresholds[feature]
                if feature == "loudness":
                    if value > threshold:
                        dominant.append(f"high_{feature}")
                elif feature == "tempo":
                    if value > 140:
                        dominant.append("high_tempo")
                    elif value < 80:
                        dominant.append("low_tempo")
                else:
                    if value > threshold:
                        dominant.append(f"high_{feature}")
                    elif (
                        value < (1 - threshold)
                        if feature != "loudness"
                        else threshold - 10
                    ):
                        dominant.append(f"low_{feature}")

        return dominant

    def _generate_cluster_description(self, centroid: Dict[str, float]) -> str:
        """Generate a human-readable description of the cluster"""
        descriptions = []

        # Energy and valence
        energy = centroid.get("energy", 0.5)
        valence = centroid.get("valence", 0.5)

        if energy > 0.7 and valence > 0.7:
            descriptions.append("Energetic and upbeat")
        elif energy > 0.7 and valence < 0.3:
            descriptions.append("High energy but melancholic")
        elif energy < 0.3 and valence > 0.7:
            descriptions.append("Calm and positive")
        elif energy < 0.3 and valence < 0.3:
            descriptions.append("Mellow and introspective")

        # Acousticness
        if centroid.get("acousticness", 0) > 0.7:
            descriptions.append("acoustic")

        # Danceability
        if centroid.get("danceability", 0) > 0.7:
            descriptions.append("danceable")

        # Instrumentalness
        if centroid.get("instrumentalness", 0) > 0.5:
            descriptions.append("instrumental")

        # Tempo
        tempo = centroid.get("tempo", 120)
        if tempo > 140:
            descriptions.append("fast-paced")
        elif tempo < 80:
            descriptions.append("slow-paced")

        return ", ".join(descriptions) if descriptions else "Mixed characteristics"

    def get_taste_evolution(self, user_id: int, db: Session) -> List[Dict[str, Any]]:
        """Analyze how user's taste evolved over time"""
        tracks = (
            db.query(Track)
            .filter(Track.user_id == user_id, Track.added_at.isnot(None))
            .order_by(Track.added_at)
            .all()
        )

        if not tracks:
            return []

        # Group tracks by quarter
        quarterly_data = {}

        for track in tracks:
            if not track.added_at:
                continue

            quarter_key = (
                f"{track.added_at.year}-Q{(track.added_at.month - 1) // 3 + 1}"
            )

            if quarter_key not in quarterly_data:
                quarterly_data[quarter_key] = []

            quarterly_data[quarter_key].append(track)

        # Calculate average features for each quarter
        evolution = []
        for quarter, quarter_tracks in quarterly_data.items():
            if len(quarter_tracks) < 3:  # Skip quarters with too few tracks
                continue

            # Calculate average features
            avg_features = {}
            for feature in self.audio_features:
                values = [
                    getattr(track, feature)
                    for track in quarter_tracks
                    if getattr(track, feature) is not None
                ]
                if values:
                    avg_features[feature] = sum(values) / len(values)

            # Get top genres (simplified - based on artist names)
            artists = [track.artist_name for track in quarter_tracks]
            top_artists = pd.Series(artists).value_counts().head(5).index.tolist()

            evolution.append(
                {
                    "period": quarter,
                    "track_count": len(quarter_tracks),
                    "avg_features": avg_features,
                    "top_artists": top_artists,
                    "date_range": {
                        "start": min(
                            track.added_at for track in quarter_tracks
                        ).isoformat(),
                        "end": max(
                            track.added_at for track in quarter_tracks
                        ).isoformat(),
                    },
                }
            )

        return sorted(evolution, key=lambda x: x["period"])

    def calculate_formative_years(
        self, birth_date, current_date=None
    ) -> Dict[str, int]:
        """Calculate formative years (ages 12-18) for nostalgia recommendations"""
        if current_date is None:
            from datetime import datetime

            current_date = datetime.now()

        birth_year = birth_date.year
        formative_start = birth_year + 12
        formative_end = birth_year + 18

        return {
            "start_year": formative_start,
            "end_year": formative_end,
            "years": list(range(formative_start, formative_end + 1)),
        }
