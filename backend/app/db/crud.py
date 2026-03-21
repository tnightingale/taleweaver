"""CRUD operations for story persistence"""
import secrets
import string
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from .models import Story
from app.config import settings


def generate_short_id(length: int = 8) -> str:
    """
    Generate URL-safe short ID using lowercase alphanumeric characters.
    
    Args:
        length: Length of the short ID (default 8)
        
    Returns:
        Random alphanumeric string (a-z0-9)
    """
    alphabet = string.ascii_lowercase + string.digits  # a-z0-9 (36 chars)
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def save_story(
    db: Session,
    story_id: str,
    title: str,
    kid_name: str,
    kid_age: int,
    story_type: str,
    transcript: str,
    duration_seconds: int,
    audio_bytes: bytes,
    genre: str = None,
    event_id: str = None,
    mood: str = None,
    length: str = None,
) -> Story:
    """
    Save story to database and write audio to filesystem.
    
    Args:
        db: SQLAlchemy database session
        story_id: UUID for the story (same as job_id)
        title: Story title
        kid_name: Child's name
        kid_age: Child's age
        story_type: 'custom' or 'historical'
        transcript: Full story text
        duration_seconds: Audio duration
        audio_bytes: MP3 audio data
        genre: Genre for custom stories
        event_id: Event ID for historical stories
        mood: Story mood (exciting, heartwarming, etc.)
        length: Story length (short, medium, long)
        
    Returns:
        Created Story database record
    """
    # Generate unique short ID
    short_id = generate_short_id()
    while db.query(Story).filter(Story.short_id == short_id).first():
        short_id = generate_short_id()
    
    # Save audio file to /storage/stories/{story_id}/audio.mp3
    story_dir = settings.storage_path / "stories" / story_id
    story_dir.mkdir(parents=True, exist_ok=True)
    audio_path = story_dir / "audio.mp3"
    audio_path.write_bytes(audio_bytes)
    
    # Create database record
    db_story = Story(
        id=story_id,
        short_id=short_id,
        title=title,
        kid_name=kid_name,
        kid_age=kid_age,
        story_type=story_type,
        genre=genre,
        event_id=event_id,
        mood=mood,
        length=length,
        transcript=transcript,
        duration_seconds=duration_seconds,
        audio_path=str(audio_path),
    )
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    
    return db_story


def get_story_by_id(db: Session, story_id: str) -> Optional[Story]:
    """
    Get story by UUID.
    
    Args:
        db: SQLAlchemy database session
        story_id: UUID of the story
        
    Returns:
        Story record or None if not found
    """
    return db.query(Story).filter(Story.id == story_id).first()


def get_story_by_short_id(db: Session, short_id: str) -> Optional[Story]:
    """
    Get story by compact short ID.
    
    Args:
        db: SQLAlchemy database session
        short_id: 8-character compact ID
        
    Returns:
        Story record or None if not found
    """
    return db.query(Story).filter(Story.short_id == short_id).first()
