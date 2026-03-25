"""SQLAlchemy models for story persistence"""
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, Float, LargeBinary, Index, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    """User account for multi-tenant story ownership"""
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # UUID
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)  # null for OAuth-only users
    display_name = Column(String, nullable=False)
    google_id = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    stories = relationship("Story", back_populates="user")


class Invite(Base):
    """Single-use invite codes for registration"""
    __tablename__ = "invites"

    id = Column(String, primary_key=True)  # UUID
    code = Column(String, unique=True, nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    used_by = Column(String, ForeignKey("users.id"), nullable=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Story(Base):
    """Persistent story record with metadata and audio reference"""
    __tablename__ = "stories"

    # Primary identifiers
    id = Column(String, primary_key=True)  # UUID (same as job_id)
    short_id = Column(String(8), unique=True, nullable=False, index=True)  # Compact permalink

    # Ownership
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    user = relationship("User", back_populates="stories")
    
    # Story metadata
    title = Column(String, nullable=False)
    kid_name = Column(String, nullable=False)
    kid_age = Column(Integer, nullable=False)
    
    # Story configuration
    story_type = Column(String, nullable=False)  # 'custom' or 'historical'
    genre = Column(String, nullable=True)  # For custom stories
    event_id = Column(String, nullable=True)  # For historical stories
    mood = Column(String, nullable=True)  # exciting, heartwarming, funny, mysterious
    length = Column(String, nullable=True)  # short, medium, long
    
    # Story content
    transcript = Column(Text, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    audio_path = Column(String, nullable=False)  # Filesystem path to MP3
    
    # Illustration metadata
    art_style = Column(String, nullable=True)  # Art style preset ID or "custom"
    has_illustrations = Column(Boolean, default=False, nullable=False)
    scene_data = Column(JSON, nullable=True)  # Scene metadata with illustration info
    cover_image_path = Column(String, nullable=True)  # Path to dedicated cover image
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class JobState(Base):
    """
    Job state for story generation (shared across gunicorn workers).
    
    Replaces in-memory jobs dict to enable multi-worker concurrency.
    Jobs are stored in database so all workers can see the same state.
    """
    __tablename__ = "job_state"
    
    # Job identification
    job_id = Column(String, primary_key=True)

    # Ownership
    user_id = Column(String, nullable=True)

    # Status tracking
    status = Column(String, nullable=False, default="processing")  # processing, complete, failed
    current_stage = Column(String)  # writing, splitting, synthesizing, etc.
    stages = Column(Text)  # JSON array of stage names
    
    # Progress tracking
    progress = Column(Float, default=0.0)  # 0-100
    progress_detail = Column(String)  # "Synthesizing segment 5 of 12"
    
    # Story metadata (populated when complete)
    title = Column(String)
    duration_seconds = Column(Integer)
    transcript = Column(Text)
    short_id = Column(String)  # Compact ID for permalink
    
    # Illustration metadata
    art_style = Column(String)
    scenes_json = Column(Text)  # JSON array of scenes
    
    # Error tracking and resume capability
    error_message = Column(Text)
    resumable = Column(Boolean, default=False, nullable=False)  # Can job be resumed?
    partial_data_json = Column(Text)  # JSON checkpoint state
    checkpoint_node = Column(String)  # Last successful node
    retry_count = Column(Integer, default=0, nullable=False)  # Retry attempts
    story_params_json = Column(Text)  # JSON: original story params for retry re-enqueue
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_job_status', 'status'),
        Index('idx_job_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Story(id={self.id}, short_id={self.short_id}, title={self.title})>"
