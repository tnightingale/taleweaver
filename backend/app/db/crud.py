"""CRUD operations for story persistence"""
import secrets
import string
import json
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import Story, JobState
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
    audio_bytes: bytes = None,
    audio_path: str = None,
    genre: str = None,
    event_id: str = None,
    mood: str = None,
    length: str = None,
    art_style: str = None,
    scene_data: dict = None,
    cover_image_path: str = None,
    user_id: str = None,
) -> Story:
    """
    Save story to database and write audio to filesystem.

    Audio can be provided either as bytes (written to disk here) or as a
    path to an existing file on disk (avoids holding large MP3 in memory).

    Args:
        db: SQLAlchemy database session
        story_id: UUID for the story (same as job_id)
        title: Story title
        kid_name: Child's name
        kid_age: Child's age
        story_type: 'custom' or 'historical'
        transcript: Full story text
        duration_seconds: Audio duration
        audio_bytes: MP3 audio data (legacy — prefer audio_path)
        audio_path: Path to existing audio file on disk
        genre: Genre for custom stories
        event_id: Event ID for historical stories
        mood: Story mood (exciting, heartwarming, etc.)
        length: Story length (short, medium, long)
        art_style: Art style preset ID or "custom"
        scene_data: Scene metadata with illustration info (JSON)

    Returns:
        Created Story database record
    """
    # Generate unique short ID
    short_id = generate_short_id()
    while db.query(Story).filter(Story.short_id == short_id).first():
        short_id = generate_short_id()

    if audio_path:
        # Audio already on disk (written by audio_stitcher directly)
        audio_path = Path(audio_path)
    elif audio_bytes is not None:
        # Legacy: write bytes to disk
        story_dir = settings.storage_path / "stories" / story_id
        story_dir.mkdir(parents=True, exist_ok=True)
        audio_path = story_dir / "audio.mp3"
        audio_path.write_bytes(audio_bytes)
    else:
        raise ValueError("Either audio_bytes or audio_path must be provided")
    
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
        art_style=art_style,
        has_illustrations=bool(scene_data),
        scene_data=scene_data,
        cover_image_path=cover_image_path,
        user_id=user_id,
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


def list_stories(
    db: Session,
    kid_name: Optional[str] = None,
    story_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "created_desc"
) -> Tuple[List[Story], int]:
    """
    List stories with optional filters, pagination, and sorting.

    Args:
        db: SQLAlchemy database session
        kid_name: Optional filter by kid name
        story_type: Optional filter by story type (custom/historical)
        user_id: Optional filter by owner user ID
        limit: Number of stories to return (default 20)
        offset: Number of stories to skip (for pagination)
        sort: Sort order - created_desc, created_asc, title, duration

    Returns:
        Tuple of (stories list, total count)
    """
    query = db.query(Story)

    # Apply filters
    if user_id:
        query = query.filter(Story.user_id == user_id)
    if kid_name:
        query = query.filter(Story.kid_name == kid_name)
    if story_type:
        query = query.filter(Story.story_type == story_type)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    if sort == "created_desc":
        query = query.order_by(Story.created_at.desc())
    elif sort == "created_asc":
        query = query.order_by(Story.created_at.asc())
    elif sort == "title":
        query = query.order_by(Story.title.asc())
    elif sort == "duration":
        query = query.order_by(Story.duration_seconds.desc())
    else:
        query = query.order_by(Story.created_at.desc())
    
    # Apply pagination
    stories = query.offset(offset).limit(limit).all()
    
    return stories, total


def get_unique_kid_names(db: Session) -> List[str]:
    """
    Get list of unique kid names from all stories.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        List of unique kid names, sorted alphabetically
    """
    result = db.query(Story.kid_name).distinct().order_by(Story.kid_name).all()
    return [name[0] for name in result]


def delete_story(db: Session, short_id: str) -> bool:
    """
    Delete story from database and remove audio file.
    
    Args:
        db: SQLAlchemy database session
        short_id: Compact short ID of story to delete
        
    Returns:
        True if deleted, False if not found
    """
    story = db.query(Story).filter(Story.short_id == short_id).first()
    if not story:
        return False
    
    # Delete audio file
    audio_path = Path(story.audio_path)
    if audio_path.exists():
        audio_path.unlink()
        # Also try to remove the parent directory if empty
        try:
            audio_path.parent.rmdir()
        except OSError:
            pass  # Directory not empty or doesn't exist
    
    # Delete database record
    db.delete(story)
    db.commit()
    
    return True


def update_story_illustrations(
    db: Session,
    short_id: str,
    scene_data: dict,
    cover_image_path: Optional[str] = None,
    art_style: Optional[str] = None,
) -> Optional[Story]:
    """
    Update illustration data on an existing story.

    Used by the regeneration flow to patch in newly generated images
    without re-running the full pipeline.

    Args:
        db: SQLAlchemy database session
        short_id: Compact short ID of story to update
        scene_data: Updated scene metadata dict (scenes, art_style_prompt, etc.)
        cover_image_path: Optional new cover image path
        art_style: Optional new art style (for style changes or adding illustrations)

    Returns:
        Updated Story record or None if not found
    """
    story = db.query(Story).filter(Story.short_id == short_id).first()
    if not story:
        return None

    story.scene_data = scene_data
    # has_illustrations is true if any scene has an image_url
    scenes = scene_data.get("scenes", [])
    story.has_illustrations = any(s.get("image_url") for s in scenes)
    if cover_image_path is not None:
        story.cover_image_path = cover_image_path
    if art_style is not None:
        story.art_style = art_style

    db.commit()
    db.refresh(story)
    return story


def update_story_title(db: Session, short_id: str, new_title: str) -> Optional[Story]:
    """
    Update story title.
    
    Args:
        db: SQLAlchemy database session
        short_id: Compact short ID of story to update
        new_title: New title for the story
        
    Returns:
        Updated Story record or None if not found
    """
    story = db.query(Story).filter(Story.short_id == short_id).first()
    if not story:
        return None
    
    story.title = new_title
    db.commit()
    db.refresh(story)
    return story


# ============================================================================
# Job State CRUD (for multi-worker job tracking)
# ============================================================================

def create_job_state(
    db: Session, job_id: str, stages: List[str], story_params: dict = None
) -> JobState:
    """
    Create new job state entry.

    Args:
        db: SQLAlchemy database session
        job_id: UUID for the job
        stages: List of stage names for this job
        story_params: Original story parameters (stored for retry re-enqueue)

    Returns:
        Created JobState record
    """
    job = JobState(
        job_id=job_id,
        status="processing",
        current_stage=stages[0] if stages else "writing",
        stages=json.dumps(stages),
        progress=0.0,
        story_params_json=json.dumps(story_params) if story_params else None,
        user_id=story_params.get("user_id") if story_params else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_state(db: Session, job_id: str) -> Optional[JobState]:
    """
    Get job state by ID.
    
    Args:
        db: SQLAlchemy database session
        job_id: Job UUID
        
    Returns:
        JobState if found, None otherwise
    """
    return db.query(JobState).filter(JobState.job_id == job_id).first()


def update_job_stage(db: Session, job_id: str, stage: str, progress: Optional[float] = None):
    """
    Update job's current stage and optionally progress.
    
    Args:
        db: SQLAlchemy database session
        job_id: Job UUID
        stage: New stage name
        progress: Optional progress percentage (0-100)
    """
    job = get_job_state(db, job_id)
    if job:
        job.current_stage = stage
        if progress is not None:
            current = job.progress or 0
            if progress >= current:
                job.progress = progress
        job.updated_at = datetime.utcnow()
        db.commit()


def update_job_progress(db: Session, job_id: str, progress: float, detail: str):
    """
    Update job progress and detail message.

    Progress is monotonically increasing — writes are skipped if the new value
    is lower than the current value. This prevents race conditions when parallel
    nodes (voice_synthesizer + illustration_generator) both update progress.

    Args:
        db: SQLAlchemy database session
        job_id: Job UUID
        progress: Progress percentage (0-100)
        detail: Detailed status message (e.g., "Synthesizing segment 5 of 12")
    """
    job = get_job_state(db, job_id)
    if job:
        current = job.progress or 0
        if progress >= current:
            job.progress = progress
            job.progress_detail = detail
            job.updated_at = datetime.utcnow()
            db.commit()


def mark_job_complete(
    db: Session,
    job_id: str,
    title: str,
    duration_seconds: int,
    transcript: str,
    short_id: str,
    art_style: Optional[str] = None,
    scenes: Optional[list] = None,
):
    """
    Mark job as complete with final metadata.
    
    Args:
        db: SQLAlchemy database session
        job_id: Job UUID
        title: Story title
        duration_seconds: Audio duration
        transcript: Full story text
        short_id: Compact short ID for permalink
        art_style: Optional art style ID
        scenes: Optional scene list with illustrations
    """
    job = get_job_state(db, job_id)
    if job:
        job.status = "complete"
        job.current_stage = "done"
        job.progress = 100.0
        job.title = title
        job.duration_seconds = duration_seconds
        job.transcript = transcript
        job.short_id = short_id
        job.art_style = art_style
        if scenes:
            job.scenes_json = json.dumps(scenes)
        job.updated_at = datetime.utcnow()
        db.commit()


def mark_job_failed(db: Session, job_id: str, error: str):
    """
    Mark job as failed with error message.
    
    Args:
        db: SQLAlchemy database session
        job_id: Job UUID
        error: Error message
    """
    job = get_job_state(db, job_id)
    if job:
        job.status = "failed"
        job.error_message = error
        job.updated_at = datetime.utcnow()
        db.commit()


def recover_orphaned_jobs(db: Session, stale_minutes: int = 5) -> int:
    """
    Mark orphaned "processing" jobs as failed.

    Called on server startup. If a job has been in "processing" status with
    no update for longer than stale_minutes, its asyncio task is presumed
    dead (server crash, OOM kill, worker restart). Mark it as failed so
    the frontend stops polling and the user sees an error.

    Args:
        db: SQLAlchemy database session
        stale_minutes: How long a job can be idle before it's considered orphaned

    Returns:
        Number of jobs recovered
    """
    cutoff = datetime.utcnow() - timedelta(minutes=stale_minutes)

    stale_jobs = db.query(JobState).filter(
        JobState.status == "processing",
        JobState.updated_at < cutoff,
    ).all()

    for job in stale_jobs:
        job.status = "failed"
        job.error_message = (
            "Story generation was interrupted (server restart or crash). "
            "Please try again."
        )
        job.updated_at = datetime.utcnow()

    if stale_jobs:
        db.commit()

    return len(stale_jobs)


def cleanup_old_jobs(db: Session, max_age_hours: int = 24) -> int:
    """
    Delete completed/failed jobs older than threshold.
    
    Args:
        db: SQLAlchemy database session
        max_age_hours: Maximum age in hours for completed/failed jobs
        
    Returns:
        Number of jobs deleted
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    deleted = db.query(JobState).filter(
        JobState.status.in_(["complete", "failed"]),
        JobState.created_at < cutoff_time
    ).delete(synchronize_session=False)
    
    db.commit()
    return deleted
