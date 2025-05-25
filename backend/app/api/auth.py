"""
Authentication API endpoints for Spotify OAuth
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid
from datetime import datetime

from app.database import get_db
from app.models import User, UserSession
from app.services.spotify_client import SpotifyClient
from app.schemas import UserCreate, UserResponse, AuthResponse

router = APIRouter()
spotify_client = SpotifyClient()

# In-memory storage for OAuth state (in production, use Redis or database)
oauth_states = {}


@router.get("/login")
async def login():
    """Initiate Spotify OAuth login"""
    try:
        auth_data = spotify_client.generate_auth_url()

        # Store OAuth state temporarily
        oauth_states[auth_data["state"]] = {
            "code_verifier": auth_data["code_verifier"],
            "created_at": datetime.utcnow(),
        }

        return {"auth_url": auth_data["auth_url"], "state": auth_data["state"]}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate auth URL: {str(e)}"
        )


@router.get("/callback")
async def auth_callback(
    code: str, state: str, error: str = None, db: Session = Depends(get_db)
):
    """Handle Spotify OAuth callback"""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    # Verify state
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    oauth_data = oauth_states.pop(state)
    code_verifier = oauth_data["code_verifier"]

    try:
        # Exchange code for tokens
        token_data = spotify_client.exchange_code_for_tokens(code, code_verifier)

        # Get user profile
        user_profile = spotify_client.get_user_profile(token_data["access_token"])

        # Create or update user
        user = db.query(User).filter(User.spotify_id == user_profile["id"]).first()

        if not user:
            user = User(
                spotify_id=user_profile["id"],
                display_name=user_profile.get("display_name"),
                email=user_profile.get("email"),
                country=user_profile.get("country"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update user info
            user.display_name = user_profile.get("display_name")
            user.email = user_profile.get("email")
            user.country = user_profile.get("country")
            db.commit()

        # Create session
        session_id = str(uuid.uuid4())
        user_session = UserSession(
            session_id=session_id,
            user_id=user.id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_expires_at=token_data["expires_at"],
        )
        db.add(user_session)
        db.commit()

        # Redirect to frontend with session
        frontend_url = f"http://127.0.0.1:3000/dashboard?session={session_id}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/onboarding")
async def complete_onboarding(
    session_id: str,
    date_of_birth: str,  # Format: YYYY-MM-DD
    db: Session = Depends(get_db),
):
    """Complete user onboarding with date of birth"""
    session = db.query(UserSession).filter(UserSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Parse and store date of birth
        dob = datetime.strptime(date_of_birth, "%Y-%m-%d")
        user.date_of_birth = dob
        db.commit()

        return {"message": "Onboarding completed successfully"}
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to complete onboarding: {str(e)}"
        )


@router.get("/me")
async def get_current_user(session_id: str, db: Session = Depends(get_db)):
    """Get current user information"""
    session = db.query(UserSession).filter(UserSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "spotify_id": user.spotify_id,
        "display_name": user.display_name,
        "email": user.email,
        "country": user.country,
        "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
        "needs_onboarding": user.date_of_birth is None,
    }


@router.post("/refresh")
async def refresh_token(session_id: str, db: Session = Depends(get_db)):
    """Refresh access token"""
    session = db.query(UserSession).filter(UserSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        # Check if token needs refresh
        if datetime.utcnow() < session.token_expires_at:
            return {"message": "Token still valid"}

        # Refresh token
        token_data = spotify_client.refresh_access_token(session.refresh_token)

        # Update session
        session.access_token = token_data["access_token"]
        session.refresh_token = token_data["refresh_token"]
        session.token_expires_at = token_data["expires_at"]
        db.commit()

        return {"message": "Token refreshed successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh token: {str(e)}"
        )


@router.post("/logout")
async def logout(session_id: str, db: Session = Depends(get_db)):
    """Logout user and invalidate session"""
    session = db.query(UserSession).filter(UserSession.session_id == session_id).first()
    if session:
        db.delete(session)
        db.commit()

    return {"message": "Logged out successfully"}


def get_current_session(session_id: str, db: Session = Depends(get_db)) -> UserSession:
    """Dependency to get current user session"""
    session = db.query(UserSession).filter(UserSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Check if token is expired
    if datetime.utcnow() >= session.token_expires_at:
        try:
            # Try to refresh token
            token_data = spotify_client.refresh_access_token(session.refresh_token)
            session.access_token = token_data["access_token"]
            session.refresh_token = token_data["refresh_token"]
            session.token_expires_at = token_data["expires_at"]
            db.commit()
        except Exception:
            raise HTTPException(status_code=401, detail="Session expired")

    return session
