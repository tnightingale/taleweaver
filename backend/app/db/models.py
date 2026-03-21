"""SQLAlchemy models for story persistence"""
from sqlalchemy import Column, String, Integer, DateTime, Text
from datetime import datetime
from .database import Base


class Story(Base):
    """Persistent story record with metadata and audio reference"""
    __tablename__ = "stories"
    
    # Primary identifiers
    id = Column(String, primary_key=True)  # UUID (same as job_id)
    short_id = Column(String(8), unique=True, nullable=False, index=True)  # Compact permalink
    
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
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Story(id={self.id}, short_id={self.short_id}, title={self.title})>"
