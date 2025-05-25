"""
Extended database models for progress tracking
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AnalysisProgress(Base):
    """Track progress of library analysis for real-time updates"""

    __tablename__ = "analysis_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        String, nullable=False
    )  # 'starting', 'fetching_tracks', 'getting_features', 'clustering', 'completed', 'failed'
    current_step = Column(String, nullable=True)  # Human-readable current step
    progress_percentage = Column(Integer, default=0)  # 0-100
    tracks_processed = Column(Integer, default=0)
    total_tracks = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
