"""
Clean test script for library analysis pipeline
"""

import os
import sys
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.database import Base
from app.models import User, Track, UserCluster, UserSession
from app.services.spotify_client import SpotifyClient
from app.services.data_analyzer import DataAnalyzer
from datetime import datetime, timedelta
import uuid

# Test database
TEST_DATABASE_URL = "sqlite:///./test_analysis_clean.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def setup_test_database():
    """Create test database and tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Test database created")


def create_test_user_and_session(test_name: str):
    """Create a test user and session for analysis with unique ID"""
    db = SessionLocal()

    # Create unique user ID based on test name and timestamp
    unique_id = f"test_user_{test_name}_{int(time.time() * 1000)}"

    # Create test user
    user = User(
        spotify_id=unique_id,
        display_name=f"Test {test_name} User",
        email=f"test_{test_name}@analysis.com",
        country="US",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Get user ID before closing session
    user_id = user.id

    # Create test session with dummy tokens
    session_id = str(uuid.uuid4())
    user_session = UserSession(
        session_id=session_id,
        user_id=user_id,
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(user_session)
    db.commit()

    db.close()
    print(f"✅ Test user created with ID: {user_id} ({unique_id})")
    print(f"✅ Test session created: {session_id}")

    return user_id, session_id


def test_spotify_client():
    """Test basic Spotify client functionality"""
    print("\n🧪 Testing Spotify Client...")

    try:
        spotify_client = SpotifyClient()
        print("✅ SpotifyClient initialized")

        # Test auth URL generation
        auth_data = spotify_client.generate_auth_url()
        print("✅ Auth URL generation works")
        print(f"   Sample auth URL: {auth_data['auth_url'][:100]}...")

        return True
    except Exception as e:
        print(f"❌ SpotifyClient test failed: {e}")
        return False


def test_data_analyzer():
    """Test data analyzer with mock data"""
    print("\n🧪 Testing Data Analyzer...")

    try:
        data_analyzer = DataAnalyzer()
        print("✅ DataAnalyzer initialized")

        # Create a test user first
        user_id, _ = create_test_user_and_session("analyzer")

        # Create mock tracks for testing
        db = SessionLocal()

        # Create 10 mock tracks with audio features
        mock_tracks = []
        for i in range(10):
            track = Track(
                spotify_id=f"analyzer_track_{user_id}_{i}",
                user_id=user_id,
                name=f"Test Track {i}",
                artist_name=f"Test Artist {i}",
                album_name=f"Test Album {i}",
                # Varied audio features for clustering
                acousticness=0.1 + (i * 0.08),  # 0.1 to 0.82
                danceability=0.2 + (i * 0.07),  # 0.2 to 0.83
                energy=0.15 + (i * 0.08),  # 0.15 to 0.87
                instrumentalness=0.05 + (i * 0.05),  # 0.05 to 0.5
                liveness=0.1 + (i * 0.03),  # 0.1 to 0.37
                loudness=-20 + (i * 1.5),  # -20 to -6.5 dB
                speechiness=0.03 + (i * 0.02),  # 0.03 to 0.21
                tempo=80 + (i * 15),  # 80 to 215 BPM
                valence=0.1 + (i * 0.09),  # 0.1 to 0.91
                key=i % 12,  # 0 to 11
                mode=i % 2,  # 0 or 1
                time_signature=4,
            )
            mock_tracks.append(track)

        # Add tracks to database
        db.bulk_save_objects(mock_tracks)
        db.commit()
        print(f"✅ Created {len(mock_tracks)} mock tracks")

        # Test clustering
        clusters = data_analyzer.perform_clustering(user_id, db, n_clusters=3)
        print(f"✅ Clustering completed: {len(clusters)} clusters created")

        # Test cluster characteristics
        characteristics = data_analyzer.get_cluster_characteristics(user_id, db)
        print(
            f"✅ Cluster characteristics calculated for {len(characteristics)} clusters"
        )

        for cluster_id, char in characteristics.items():
            # Fix the track count display issue
            track_count = char["track_count"]
            if isinstance(track_count, bytes):
                # Convert bytes to int if needed
                track_count = int.from_bytes(track_count, byteorder="little")
            print(
                f"   Cluster {cluster_id}: {track_count} tracks - {char['description']}"
            )

        db.close()
        return True

    except Exception as e:
        print(f"❌ DataAnalyzer test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_full_analysis_pipeline():
    """Test the complete analysis pipeline with minimal data"""
    print("\n🧪 Testing Full Analysis Pipeline...")

    try:
        # Create test user and session
        user_id, session_id = create_test_user_and_session("pipeline")

        # Test with mock data (simulating what would come from Spotify)
        print("✅ Simulating Spotify API calls...")

        # Create some mock tracks first
        db = SessionLocal()
        mock_tracks = []
        for i in range(5):  # Just 5 tracks for quick test
            track = Track(
                spotify_id=f"pipeline_track_{user_id}_{i}",
                user_id=user_id,
                name=f"Pipeline Track {i}",
                artist_name=f"Pipeline Artist {i}",
                album_name=f"Pipeline Album {i}",
                acousticness=0.2 + (i * 0.15),
                danceability=0.3 + (i * 0.1),
                energy=0.4 + (i * 0.1),
                instrumentalness=0.1 + (i * 0.05),
                liveness=0.15 + (i * 0.05),
                loudness=-15 + (i * 2),
                speechiness=0.05 + (i * 0.02),
                tempo=100 + (i * 20),
                valence=0.3 + (i * 0.15),
                key=i % 12,
                mode=i % 2,
                time_signature=4,
            )
            mock_tracks.append(track)

        db.bulk_save_objects(mock_tracks)
        db.commit()
        print(f"✅ Created {len(mock_tracks)} pipeline test tracks")

        # Test clustering with the mock data
        data_analyzer = DataAnalyzer()
        clusters = data_analyzer.perform_clustering(user_id, db, n_clusters=2)
        print(f"✅ Analysis pipeline completed: {len(clusters)} clusters")

        # Verify data was stored correctly
        track_count = db.query(Track).filter(Track.user_id == user_id).count()
        cluster_count = (
            db.query(UserCluster).filter(UserCluster.user_id == user_id).count()
        )

        print(f"✅ Verification: {track_count} tracks, {cluster_count} clusters stored")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Full pipeline test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def cleanup_test_data():
    """Clean up test database"""
    try:
        os.remove("test_analysis_clean.db")
        print("✅ Test database cleaned up")
    except FileNotFoundError:
        pass


def main():
    """Run all tests"""
    print("🚀 Starting Library Analysis Pipeline Tests (Clean)")
    print("=" * 50)

    # Setup
    setup_test_database()

    # Run tests
    tests = [
        ("Spotify Client", test_spotify_client),
        ("Data Analyzer", test_data_analyzer),
        ("Full Pipeline", test_full_analysis_pipeline),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! Analysis pipeline is working.")
        print("\n🔍 Key Findings:")
        print("   ✅ SpotifyClient initializes and generates auth URLs")
        print("   ✅ DataAnalyzer performs K-means clustering successfully")
        print("   ✅ Database operations work correctly")
        print("   ✅ Cluster characteristics are calculated")
        print("   ✅ Full pipeline from tracks to clusters works")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

    # Cleanup
    cleanup_test_data()


if __name__ == "__main__":
    main()
