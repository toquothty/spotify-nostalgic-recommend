"""
Pydantic schemas for request/response models
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserCreate(BaseModel):
    spotify_id: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    country: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    spotify_id: str
    display_name: Optional[str]
    email: Optional[str]
    country: Optional[str]
    date_of_birth: Optional[datetime]
    needs_onboarding: bool

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    auth_url: str
    state: str


class OnboardingRequest(BaseModel):
    session_id: str
    date_of_birth: str  # YYYY-MM-DD format


class TrackResponse(BaseModel):
    id: int
    spotify_id: str
    name: str
    artist_name: str
    album_name: Optional[str]
    duration_ms: Optional[int]
    popularity: Optional[int]
    explicit: bool
    preview_url: Optional[str]
    external_url: Optional[str]
    image_url: Optional[str]
    added_at: Optional[datetime]
    release_date: Optional[str]

    # Audio features
    acousticness: Optional[float]
    danceability: Optional[float]
    energy: Optional[float]
    instrumentalness: Optional[float]
    liveness: Optional[float]
    loudness: Optional[float]
    speechiness: Optional[float]
    tempo: Optional[float]
    valence: Optional[float]
    key: Optional[int]
    mode: Optional[int]
    time_signature: Optional[int]

    cluster_id: Optional[int]

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    id: int
    spotify_track_id: str
    track_name: str
    artist_name: str
    album_name: Optional[str]
    preview_url: Optional[str]
    external_url: Optional[str]
    image_url: Optional[str]
    recommendation_type: str
    source_cluster_id: Optional[int]
    confidence_score: Optional[float]
    user_liked: Optional[bool]
    user_already_knew: Optional[bool]
    created_at: datetime

    class Config:
        from_attributes = True


class ClusterResponse(BaseModel):
    id: int
    cluster_id: int
    centroid_data: Dict[str, Any]
    track_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    total_tracks: int
    clusters: List[ClusterResponse]
    top_genres: List[Dict[str, Any]]
    audio_features_summary: Dict[str, float]
    formative_years: Optional[Dict[str, int]]


class FeedbackRequest(BaseModel):
    recommendation_id: int
    liked: Optional[bool] = None
    already_knew: Optional[bool] = None


class DataAnalysisRequest(BaseModel):
    session_id: str
    track_limit: Optional[int] = 1000


class RecommendationRequest(BaseModel):
    session_id: str
    recommendation_type: str = "cluster"  # "cluster" or "nostalgia"
    limit: Optional[int] = 20


class TasteEvolutionResponse(BaseModel):
    period: str  # "2023-Q1", "2023-Q2", etc.
    track_count: int
    avg_features: Dict[str, float]
    top_genres: List[str]
    date_range: Dict[str, str]


class BillboardChartResponse(BaseModel):
    chart_date: datetime
    chart_type: str
    position: int
    track_name: str
    artist_name: str
    spotify_track_id: Optional[str]

    class Config:
        from_attributes = True
