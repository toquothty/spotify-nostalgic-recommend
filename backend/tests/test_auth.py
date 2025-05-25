"""
Tests for authentication endpoints
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid

from app.main import app
from app.database import get_db, Base
from app.models import User, UserSession

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Create tables for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user_session(setup_database):
    """Create a test user and session"""
    db = TestingSessionLocal()

    # Create test user
    user = User(
        spotify_id="test_spotify_id",
        display_name="Test User",
        email="test@example.com",
        country="US",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create test session
    session_id = str(uuid.uuid4())
    user_session = UserSession(
        session_id=session_id,
        user_id=user.id,
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(user_session)
    db.commit()

    db.close()
    return {"user": user, "session_id": session_id}


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_login_endpoint(self):
        """Test login endpoint returns auth URL"""
        response = client.get("/api/auth/login")
        assert response.status_code == 200

        data = response.json()
        assert "auth_url" in data
        assert "state" in data
        assert "accounts.spotify.com/authorize" in data["auth_url"]

    def test_get_current_user_valid_session(self, test_user_session):
        """Test getting current user with valid session"""
        session_id = test_user_session["session_id"]

        response = client.get(f"/api/auth/me?session_id={session_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["spotify_id"] == "test_spotify_id"
        assert data["display_name"] == "Test User"
        assert data["email"] == "test@example.com"
        assert data["needs_onboarding"] is True  # No date_of_birth set

    def test_get_current_user_invalid_session(self, setup_database):
        """Test getting current user with invalid session"""
        response = client.get("/api/auth/me?session_id=invalid_session")
        assert response.status_code == 401
        assert "Invalid session" in response.json()["detail"]

    def test_complete_onboarding_success(self, test_user_session):
        """Test successful onboarding completion"""
        session_id = test_user_session["session_id"]

        # Test with form data (as the frontend now sends)
        response = client.post(
            "/api/auth/onboarding",
            data={"session_id": session_id, "date_of_birth": "1990-05-15"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Onboarding completed successfully"

        # Verify user was updated (backend returns ISO format with time)
        user_response = client.get(f"/api/auth/me?session_id={session_id}")
        user_data = user_response.json()
        assert user_data["date_of_birth"] == "1990-05-15T00:00:00"
        assert user_data["needs_onboarding"] is False

    def test_complete_onboarding_invalid_session(self, setup_database):
        """Test onboarding with invalid session"""
        response = client.post(
            "/api/auth/onboarding",
            data={"session_id": "invalid_session", "date_of_birth": "1990-05-15"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 401
        assert "Invalid session" in response.json()["detail"]

    def test_complete_onboarding_invalid_date_format(self, test_user_session):
        """Test onboarding with invalid date format"""
        session_id = test_user_session["session_id"]

        response = client.post(
            "/api/auth/onboarding",
            data={"session_id": session_id, "date_of_birth": "invalid-date"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    def test_complete_onboarding_missing_parameters(self, test_user_session):
        """Test onboarding with missing parameters"""
        session_id = test_user_session["session_id"]

        # Missing date_of_birth
        response = client.post(
            "/api/auth/onboarding",
            data={"session_id": session_id},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 422  # Unprocessable Entity

    def test_logout_success(self, test_user_session):
        """Test successful logout"""
        session_id = test_user_session["session_id"]

        # Use form data for logout (matching frontend)
        response = client.post(
            "/api/auth/logout",
            data={"session_id": session_id},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

        # Verify session is invalidated
        user_response = client.get(f"/api/auth/me?session_id={session_id}")
        assert user_response.status_code == 401

    def test_logout_invalid_session(self, setup_database):
        """Test logout with invalid session (should still succeed)"""
        response = client.post(
            "/api/auth/logout",
            data={"session_id": "invalid_session"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"


class TestOnboardingValidation:
    """Test onboarding validation logic"""

    def test_valid_dates(self, test_user_session):
        """Test various valid date formats"""
        session_id = test_user_session["session_id"]

        valid_dates = ["1990-01-01", "2000-12-31", "1985-06-15"]

        for date in valid_dates:
            # Reset user for each test
            db = TestingSessionLocal()
            user = db.query(User).filter(User.spotify_id == "test_spotify_id").first()
            user.date_of_birth = None
            db.commit()
            db.close()

            response = client.post(
                "/api/auth/onboarding",
                data={"session_id": session_id, "date_of_birth": date},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            assert response.status_code == 200, f"Failed for date: {date}"

    def test_edge_case_dates(self, test_user_session):
        """Test edge case dates"""
        session_id = test_user_session["session_id"]

        # Leap year
        response = client.post(
            "/api/auth/onboarding",
            data={"session_id": session_id, "date_of_birth": "2000-02-29"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200

        # Reset user
        db = TestingSessionLocal()
        user = db.query(User).filter(User.spotify_id == "test_spotify_id").first()
        user.date_of_birth = None
        db.commit()
        db.close()

        # Very old date (but valid)
        response = client.post(
            "/api/auth/onboarding",
            data={"session_id": session_id, "date_of_birth": "1920-01-01"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])
