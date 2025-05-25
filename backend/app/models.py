"""
Database models for the Spotify Nostalgic Recommender
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model for storing user information and preferences"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    spotify_id = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    country = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tracks = relationship("Track", back_populates="user")
    clusters = relationship("UserCluster", back_populates="user")
    recommendations = relationship("Recommendation", back_populates="user")


class Track(Base):
    """Track model for storing user's liked songs and their features"""
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    spotify_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    artist_name = Column(String, nullable=False)
    album_name = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    popularity = Column(Integer, nullable=True)
    explicit = Column(Boolean, default=False)
    preview_url = Column(String, nullable=True)
    external_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    added_at = Column(DateTime, nullable=True)
    release_date = Column(String, nullable=True)
    
    # Audio features
    acousticness = Column(Float, nullable=True)
    danceability = Column(Float, nullable=True)
    energy = Column(Float, nullable=True)
    instrumentalness = Column(Float, nullable=True)
    liveness = Column(Float, nullable=True)
    loudness = Column(Float, nullable=True)
    speechiness = Column(Float, nullable=True)
    tempo = Column(Float, nullable=True)
    valence = Column(Float, nullable=True)
    key = Column(Integer, nullable=True)
    mode = Column(Integer, nullable=True)
    time_signature = Column(Integer, nullable=True)
    
    # Clustering
    cluster_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="tracks")


class UserCluster(Base):
    """User's music taste clusters from K-means analysis"""
    __tablename__ = "user_clusters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cluster_id = Column(Integer, nullable=False)
    centroid_data = Column(JSON, nullable=False)  # Store cluster centroid features
    track_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="clusters")


class Recommendation(Base):
    """Generated recommendations for users"""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    spotify_track_id = Column(String, nullable=False)
    track_name = Column(String, nullable=False)
    artist_name = Column(String, nullable=False)
    album_name = Column(String, nullable=True)
    preview_url = Column(String, nullable=True)
    external_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    
    # Recommendation metadata
    recommendation_type = Column(String, nullable=False)  # 'cluster', 'nostalgia'
    source_cluster_id = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # User feedback
    user_liked = Column(Boolean, nullable=True)
    user_already_knew = Column(Boolean, nullable=True)
    user_feedback_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="recommendations")


class BillboardChart(Base):
    """Billboard chart data for nostalgia recommendations"""
    __tablename__ = "billboard_charts"

    id = Column(Integer, primary_key=True, index=True)
    chart_date = Column(DateTime, nullable=False)
    chart_type = Column(String, nullable=False)  # 'hot-100', 'rock', 'pop', etc.
    position = Column(Integer, nullable=False)
    track_name = Column(String, nullable=False)
    artist_name = Column(String, nullable=False)
    spotify_track_id = Column(String, nullable=True)
    
    # Audio features (if found on Spotify)
    acousticness = Column(Float, nullable=True)
    danceability = Column(Float, nullable=True)
    energy = Column(Float, nullable=True)
    instrumentalness = Column(Float, nullable=True)
    liveness = Column(Float, nullable=True)
    loudness = Column(Float, nullable=True)
    speechiness = Column(Float, nullable=True)
    tempo = Column(Float, nullable=True)
    valence = Column(Float, nullable=True)
    key = Column(Integer, nullable=True)
    mode = Column(Integer, nullable=True)
    time_signature = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())


class UserSession(Base):
    """User session management"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)
    last_recommendation_at = Column(DateTime, nullable=True)
    recommendation_count_today = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
