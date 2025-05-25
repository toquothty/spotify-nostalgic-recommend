"""
Spotify API client with OAuth 2.0 + PKCE authentication
"""

import os
import base64
import hashlib
import secrets
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Dict, List, Optional, Any
import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SpotifyClient:
    """Spotify API client with OAuth 2.0 + PKCE support"""

    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing required Spotify API credentials")

        self.scope = (
            "user-library-read user-library-modify user-read-private user-read-email"
        )

    def generate_auth_url(self) -> Dict[str, str]:
        """Generate authorization URL with PKCE"""
        # Generate code verifier and challenge for PKCE
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("utf-8")).digest()
            )
            .decode("utf-8")
            .rstrip("=")
        )

        # Generate state for security
        state = secrets.token_urlsafe(32)

        auth_url = (
            f"https://accounts.spotify.com/authorize?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"redirect_uri={self.redirect_uri}&"
            f"code_challenge_method=S256&"
            f"code_challenge={code_challenge}&"
            f"state={state}&"
            f"scope={self.scope}"
        )

        return {"auth_url": auth_url, "code_verifier": code_verifier, "state": state}

    def exchange_code_for_tokens(self, code: str, code_verifier: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        token_url = "https://accounts.spotify.com/api/token"

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }

        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise Exception(f"Failed to exchange code for tokens: {response.text}")

        token_data = response.json()

        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(
            seconds=token_data.get("expires_in", 3600)
        )

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "expires_at": expires_at,
            "token_type": token_data.get("token_type", "Bearer"),
            "scope": token_data.get("scope", self.scope),
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        token_url = "https://accounts.spotify.com/api/token"

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            raise Exception(f"Failed to refresh token: {response.text}")

        token_data = response.json()
        expires_at = datetime.utcnow() + timedelta(
            seconds=token_data.get("expires_in", 3600)
        )

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get(
                "refresh_token", refresh_token
            ),  # May not return new refresh token
            "expires_at": expires_at,
            "token_type": token_data.get("token_type", "Bearer"),
        }

    def get_spotify_client(self, access_token: str) -> spotipy.Spotify:
        """Get authenticated Spotify client"""
        return spotipy.Spotify(auth=access_token)

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile information"""
        sp = self.get_spotify_client(access_token)
        return sp.current_user()

    def get_user_saved_tracks_count(self, access_token: str) -> int:
        """Get total count of user's saved tracks (liked songs)"""
        sp = self.get_spotify_client(access_token)

        try:
            # Get first batch to get total count
            results = sp.current_user_saved_tracks(limit=1, offset=0)
            return results.get("total", 0)
        except Exception as e:
            logger.error(f"Failed to get saved tracks count: {e}")
            return 0

    def get_user_saved_tracks(
        self, access_token: str, limit: int = 1000, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's saved tracks (liked songs)"""
        sp = self.get_spotify_client(access_token)

        tracks = []
        batch_size = 50  # Spotify API limit

        while len(tracks) < limit:
            current_limit = min(batch_size, limit - len(tracks))
            results = sp.current_user_saved_tracks(
                limit=current_limit, offset=offset + len(tracks)
            )

            if not results["items"]:
                break

            tracks.extend(results["items"])

            if len(results["items"]) < current_limit:
                break

        return tracks

    def get_audio_features(
        self, access_token: str, track_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get audio features for multiple tracks"""
        sp = self.get_spotify_client(access_token)

        # Spotify API allows max 100 tracks per request
        batch_size = 100
        all_features = []

        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i : i + batch_size]
            features = sp.audio_features(batch)
            all_features.extend([f for f in features if f is not None])

        return all_features

    def get_recommendations(
        self,
        access_token: str,
        seed_tracks: Optional[List[str]] = None,
        seed_artists: Optional[List[str]] = None,
        seed_genres: Optional[List[str]] = None,
        target_features: Optional[Dict[str, float]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get track recommendations based on seeds and target features"""
        sp = self.get_spotify_client(access_token)

        kwargs = {"limit": limit}

        if seed_tracks:
            kwargs["seed_tracks"] = seed_tracks[:5]  # Max 5 seeds
        if seed_artists:
            kwargs["seed_artists"] = seed_artists[:5]
        if seed_genres:
            kwargs["seed_genres"] = seed_genres[:5]

        # Add target audio features
        if target_features:
            for feature, value in target_features.items():
                if feature in [
                    "acousticness",
                    "danceability",
                    "energy",
                    "instrumentalness",
                    "liveness",
                    "loudness",
                    "speechiness",
                    "tempo",
                    "valence",
                ]:
                    kwargs[f"target_{feature}"] = value

        try:
            recommendations = sp.recommendations(**kwargs)
            return recommendations.get("tracks", [])
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []

    def search_tracks(
        self, access_token: str, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for tracks"""
        sp = self.get_spotify_client(access_token)

        try:
            results = sp.search(q=query, type="track", limit=limit)
            return results.get("tracks", {}).get("items", [])
        except Exception as e:
            logger.error(f"Failed to search tracks: {e}")
            return []

    def add_tracks_to_library(self, access_token: str, track_ids: List[str]) -> bool:
        """Add tracks to user's library"""
        sp = self.get_spotify_client(access_token)

        try:
            # Spotify API allows max 50 tracks per request
            batch_size = 50
            for i in range(0, len(track_ids), batch_size):
                batch = track_ids[i : i + batch_size]
                sp.current_user_saved_tracks_add(batch)
            return True
        except Exception as e:
            logger.error(f"Failed to add tracks to library: {e}")
            return False

    def get_available_genre_seeds(self, access_token: str) -> List[str]:
        """Get available genre seeds for recommendations"""
        sp = self.get_spotify_client(access_token)

        try:
            genres = sp.recommendation_genre_seeds()
            return genres.get("genres", [])
        except Exception as e:
            logger.error(f"Failed to get genre seeds: {e}")
            return []
