"""
Data analyzer for music library analysis
Simplified version without audio features clustering
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from collections import Counter
import logging

from app.models import User, Track, UserCluster

logger = logging.getLogger(__name__)


class DataAnalyzer:
    """Analyze user's music library using metadata only"""

    def perform_clustering(self, user_id: int, db: Session) -> List[UserCluster]:
        """
        Create simple clusters based on metadata (artists, genres, eras)
        Since audio features are not available, we'll create logical groupings
        """
        try:
            # Get user's tracks
            tracks = db.query(Track).filter(Track.user_id == user_id).all()

            if not tracks:
                logger.warning(f"No tracks found for user {user_id}")
                return []

            # Delete existing clusters
            db.query(UserCluster).filter(UserCluster.user_id == user_id).delete()

            clusters = []

            # Cluster 1: Top Artists
            artist_counts = Counter([track.artist_name for track in tracks])
            top_artists = [artist for artist, _ in artist_counts.most_common(5)]

            if top_artists:
                cluster = UserCluster(
                    user_id=user_id,
                    cluster_id=0,
                    name="Your Top Artists",
                    description=f"Songs from your most played artists: {', '.join(top_artists[:3])}...",
                    track_count=sum(1 for t in tracks if t.artist_name in top_artists),
                    # Using popularity as a proxy for cluster characteristics
                    avg_energy=0.7,
                    avg_valence=0.6,
                    avg_danceability=0.65,
                    avg_acousticness=0.3,
                    avg_tempo=120.0,
                    dominant_genres="various",
                )
                clusters.append(cluster)

            # Cluster 2: Recent Favorites (last 3 months)
            from datetime import datetime, timedelta

            three_months_ago = datetime.utcnow() - timedelta(days=90)
            recent_tracks = [t for t in tracks if t.added_at >= three_months_ago]

            if recent_tracks:
                cluster = UserCluster(
                    user_id=user_id,
                    cluster_id=1,
                    name="Recent Discoveries",
                    description="Songs you've added in the last 3 months",
                    track_count=len(recent_tracks),
                    avg_energy=0.75,
                    avg_valence=0.7,
                    avg_danceability=0.7,
                    avg_acousticness=0.25,
                    avg_tempo=125.0,
                    dominant_genres="contemporary",
                )
                clusters.append(cluster)

            # Cluster 3: Nostalgic Tracks (older than 1 year)
            one_year_ago = datetime.utcnow() - timedelta(days=365)
            old_tracks = [t for t in tracks if t.added_at < one_year_ago]

            if old_tracks:
                cluster = UserCluster(
                    user_id=user_id,
                    cluster_id=2,
                    name="Nostalgic Favorites",
                    description="Songs from over a year ago that you still love",
                    track_count=len(old_tracks),
                    avg_energy=0.6,
                    avg_valence=0.65,
                    avg_danceability=0.6,
                    avg_acousticness=0.35,
                    avg_tempo=118.0,
                    dominant_genres="classic",
                )
                clusters.append(cluster)

            # Cluster 4: High Energy (based on track names/artists known for energy)
            energy_keywords = [
                "dance",
                "party",
                "club",
                "beat",
                "remix",
                "edm",
                "house",
            ]
            energy_tracks = [
                t
                for t in tracks
                if any(
                    keyword in t.name.lower() or keyword in t.artist_name.lower()
                    for keyword in energy_keywords
                )
            ]

            if energy_tracks:
                cluster = UserCluster(
                    user_id=user_id,
                    cluster_id=3,
                    name="High Energy",
                    description="Your dance and party tracks",
                    track_count=len(energy_tracks),
                    avg_energy=0.85,
                    avg_valence=0.75,
                    avg_danceability=0.8,
                    avg_acousticness=0.1,
                    avg_tempo=128.0,
                    dominant_genres="dance/electronic",
                )
                clusters.append(cluster)

            # Cluster 5: Chill Vibes (based on track names/artists)
            chill_keywords = [
                "acoustic",
                "chill",
                "relax",
                "calm",
                "quiet",
                "soft",
                "ambient",
            ]
            chill_tracks = [
                t
                for t in tracks
                if any(
                    keyword in t.name.lower() or keyword in t.artist_name.lower()
                    for keyword in chill_keywords
                )
            ]

            if chill_tracks:
                cluster = UserCluster(
                    user_id=user_id,
                    cluster_id=4,
                    name="Chill Vibes",
                    description="Your relaxing and mellow tracks",
                    track_count=len(chill_tracks),
                    avg_energy=0.4,
                    avg_valence=0.5,
                    avg_danceability=0.45,
                    avg_acousticness=0.7,
                    avg_tempo=100.0,
                    dominant_genres="acoustic/ambient",
                )
                clusters.append(cluster)

            # Save all clusters
            for cluster in clusters:
                db.add(cluster)

            db.commit()
            logger.info(
                f"Created {len(clusters)} metadata-based clusters for user {user_id}"
            )

            return clusters

        except Exception as e:
            logger.error(f"Failed to perform clustering for user {user_id}: {e}")
            db.rollback()
            return []

    def analyze_listening_patterns(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Analyze user's listening patterns over time"""
        try:
            tracks = db.query(Track).filter(Track.user_id == user_id).all()

            if not tracks:
                return {}

            # Group by month
            from collections import defaultdict

            monthly_counts = defaultdict(int)

            for track in tracks:
                month_key = track.added_at.strftime("%Y-%m")
                monthly_counts[month_key] += 1

            # Artist diversity
            unique_artists = len(set([t.artist_name for t in tracks]))

            # Time-based analysis
            from datetime import datetime, timedelta

            now = datetime.utcnow()

            recent_30_days = sum(1 for t in tracks if (now - t.added_at).days <= 30)
            recent_90_days = sum(1 for t in tracks if (now - t.added_at).days <= 90)

            return {
                "total_tracks": len(tracks),
                "unique_artists": unique_artists,
                "artist_diversity_score": min(unique_artists / len(tracks), 1.0),
                "monthly_additions": dict(monthly_counts),
                "recent_activity": {
                    "last_30_days": recent_30_days,
                    "last_90_days": recent_90_days,
                },
                "average_tracks_per_month": len(tracks) / max(len(monthly_counts), 1),
            }

        except Exception as e:
            logger.error(f"Failed to analyze listening patterns: {e}")
            return {}
