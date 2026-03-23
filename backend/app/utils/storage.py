"""
Storage utilities for illustrations and temp audio segments
"""
import logging
import shutil
from pathlib import Path
from typing import Optional, List

from app.config import settings

logger = logging.getLogger(__name__)


def save_illustration(story_id: str, scene_index: int, image_bytes: bytes) -> str:
    """
    Save illustration to filesystem.
    
    Args:
        story_id: Story UUID
        scene_index: Scene index (0-based)
        image_bytes: PNG image data
        
    Returns:
        Filesystem path where image was saved
    """
    story_dir = settings.storage_path / "stories" / story_id
    story_dir.mkdir(parents=True, exist_ok=True)
    
    image_path = story_dir / f"scene_{scene_index}.png"
    image_path.write_bytes(image_bytes)
    
    logger.info(f"Saved illustration: {image_path} ({len(image_bytes)} bytes)")
    return str(image_path)


def get_illustration_url(story_id: str, scene_index: int) -> str:
    """
    Get public URL for illustration.
    
    Args:
        story_id: Story UUID
        scene_index: Scene index
        
    Returns:
        Public URL to access the illustration
    """
    return f"/storage/stories/{story_id}/scene_{scene_index}.png"


def delete_story_illustrations(story_id: str) -> int:
    """
    Delete all illustrations for a story.
    
    Args:
        story_id: Story UUID
        
    Returns:
        Number of files deleted
    """
    story_dir = settings.storage_path / "stories" / story_id
    
    if not story_dir.exists():
        return 0
    
    deleted_count = 0
    for scene_file in story_dir.glob("scene_*.png"):
        scene_file.unlink()
        deleted_count += 1
        logger.info(f"Deleted illustration: {scene_file}")
    
    return deleted_count


def illustration_exists(story_id: str, scene_index: int) -> bool:
    """
    Check if illustration file exists.
    
    Args:
        story_id: Story UUID
        scene_index: Scene index
        
    Returns:
        True if file exists
    """
    image_path = settings.storage_path / "stories" / story_id / f"scene_{scene_index}.png"
    return image_path.exists()


def save_cover_image(story_id: str, image_bytes: bytes) -> str:
    """Save cover image to filesystem. Returns filesystem path."""
    story_dir = settings.storage_path / "stories" / story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    image_path = story_dir / "cover.png"
    image_path.write_bytes(image_bytes)

    logger.info(f"Saved cover image: {image_path} ({len(image_bytes)} bytes)")
    return str(image_path)


def get_cover_image_url(story_id: str) -> str:
    """Get public URL for cover image."""
    return f"/storage/stories/{story_id}/cover.png"


# ============================================================================
# Temp Audio Segment Storage (for resume capability)
# ============================================================================

def save_temp_audio_segment(job_id: str, index: int, audio_bytes: bytes) -> str:
    """
    Save audio segment to temp storage for resume capability.
    
    Segments are saved as individual MP3 files so that if job fails,
    we can resume from the last successful segment instead of re-synthesizing all.
    
    Args:
        job_id: Job UUID
        index: Segment index (0-based)
        audio_bytes: MP3 audio data
        
    Returns:
        Path where segment was saved
    """
    temp_dir = settings.storage_path / "temp" / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    segment_path = temp_dir / f"segment_{index}.mp3"
    segment_path.write_bytes(audio_bytes)
    
    logger.debug(f"Saved temp audio segment {index}: {segment_path} ({len(audio_bytes)} bytes)")
    return str(segment_path)


def load_temp_audio_segments(job_id: str) -> List[bytes]:
    """
    Load previously saved audio segments (for resume).
    
    Used when resuming a job that failed during voice synthesis.
    Loads segments 0, 1, 2, ... until a gap is found.
    
    Args:
        job_id: Job UUID
        
    Returns:
        List of audio segment bytes in order
    """
    temp_dir = settings.storage_path / "temp" / job_id
    if not temp_dir.exists():
        return []
    
    segments = []
    for i in range(100):  # Max reasonable segment count
        segment_path = temp_dir / f"segment_{i}.mp3"
        if not segment_path.exists():
            break
        segments.append(segment_path.read_bytes())
    
    if segments:
        logger.info(f"📥 Loaded {len(segments)} temp audio segments for job {job_id}")
    
    return segments


def cleanup_temp_audio(job_id: str):
    """
    Remove temp audio files after job completes or permanently fails.
    
    Should be called when:
    - Job completes successfully (segments no longer needed)
    - Job permanently fails (not resumable)
    - Job is older than 24 hours (cleanup task)
    
    Args:
        job_id: Job UUID
    """
    temp_dir = settings.storage_path / "temp" / job_id
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        logger.info(f"🗑️ Cleaned up temp audio for job {job_id}")
