"""
Timestamp Calculator Node - Calculates scene timestamps based on audio duration
"""
import logging

from app.graph.state import StoryState

logger = logging.getLogger(__name__)


def timestamp_calculator(state: StoryState) -> dict:
    """
    Calculate timestamps for each scene based on word count distribution.
    
    Runs after audio_stitcher when we know the total duration.
    Allocates time proportionally based on word counts.
    
    Returns:
        dict with updated 'scenes' containing accurate timestamps
    """
    scenes = state.get("scenes")
    
    # Skip if no scenes
    if not scenes or len(scenes) == 0:
        return {"scenes": scenes}
    
    total_duration = state.get("duration_seconds", 0)
    
    if total_duration == 0:
        logger.warning("Total duration is 0, cannot calculate timestamps")
        return {"scenes": scenes}
    
    # Calculate total word count across all scenes
    total_words = sum(scene["word_count"] for scene in scenes)
    
    if total_words == 0:
        logger.warning("Total word count is 0, using equal distribution")
        # Fallback: distribute time equally
        scene_duration = total_duration / len(scenes)
        current_time = 0.0
        
        for scene in scenes:
            scene["timestamp_start"] = current_time
            scene["timestamp_end"] = current_time + scene_duration
            current_time += scene_duration
    else:
        # Distribute time proportionally based on word count
        current_time = 0.0
        
        for scene in scenes:
            # Calculate this scene's duration based on its proportion of total words
            scene_proportion = scene["word_count"] / total_words
            scene_duration = scene_proportion * total_duration
            
            scene["timestamp_start"] = round(current_time, 2)
            scene["timestamp_end"] = round(current_time + scene_duration, 2)
            
            current_time += scene_duration
        
        # Ensure last scene ends exactly at total duration (avoid rounding errors)
        if scenes:
            scenes[-1]["timestamp_end"] = float(total_duration)
    
    logger.info(f"Calculated timestamps for {len(scenes)} scenes (total duration: {total_duration}s)")
    
    return {"scenes": scenes}
