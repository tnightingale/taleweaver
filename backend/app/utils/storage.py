"""
Storage utilities for illustrations
"""
import logging
from pathlib import Path
from typing import Optional

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
