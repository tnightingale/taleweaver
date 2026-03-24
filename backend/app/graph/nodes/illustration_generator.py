"""
Illustration Generator Node - Generates images for each scene
"""
import logging
import yaml
from pathlib import Path

from app.graph.state import StoryState
from app.services.illustration.factory import get_illustration_provider
from app.utils.storage import save_illustration, get_illustration_url

logger = logging.getLogger(__name__)

# Load art styles data
DATA_DIR = Path(__file__).parent.parent.parent / "data"
with open(DATA_DIR / "art_styles.yaml") as f:
    ART_STYLES = {style["id"]: style for style in yaml.safe_load(f)}


async def illustration_generator(state: StoryState) -> dict:
    """
    Generate illustrations for all scenes.
    
    Runs in parallel with voice_synthesizer.
    Uses image-to-image chaining for character consistency.
    
    Returns:
        dict with updated 'scenes' containing image_path and image_url
    """
    # Skip if no art style or no scenes
    if not state.get("art_style") or not state.get("scenes"):
        logger.info("Skipping illustration generation (no art style or scenes)")
        return {"scenes": state.get("scenes")}
    
    scenes = state["scenes"]
    art_style_id = state["art_style"]
    
    # Get art style prompt
    if art_style_id == "custom":
        art_style_prompt = state.get("custom_art_style_prompt", "")
    else:
        art_style_data = ART_STYLES.get(art_style_id)
        if not art_style_data or not art_style_data.get("prompt"):
            logger.error(f"Unknown or invalid art style: {art_style_id}")
            return {"scenes": scenes}
        art_style_prompt = art_style_data["prompt"]
    
    logger.info(f"Generating {len(scenes)} illustrations with style: {art_style_id}")
    
    provider = get_illustration_provider()
    logger.info(f"Using provider: {provider.get_provider_info()['name']}")
    
    # We need a job_id or story_id to save images
    story_id = state.get("job_id", "temp")
    
    previous_image_url = None
    successful_count = 0
    failed_count = 0
    errors = []  # Track all errors for detailed reporting
    
    for i, scene in enumerate(scenes):
        try:
            logger.info(f"🎨 Generating illustration {i+1}/{len(scenes)}: {scene['beat_name']}")
            
            # Build full prompt with character consistency
            char_desc = state.get("character_description", "")
            if i == 0 and char_desc:
                # First image: include character description
                full_prompt = f"{char_desc}. {scene['illustration_prompt']}"
            else:
                # Subsequent images: rely on reference image for character consistency
                full_prompt = scene["illustration_prompt"]
            
            # Generate image
            image_bytes = await provider.generate_image(
                prompt=full_prompt,
                art_style=art_style_prompt,
                reference_image_url=previous_image_url,
                aspect_ratio=state.get("aspect_ratio", "4:3"),
                resolution=state.get("resolution", "2K"),
            )
            
            # Save to storage
            image_path = save_illustration(story_id, i, image_bytes)
            image_url = get_illustration_url(story_id, i)
            
            # Update THIS scene's metadata immediately
            scene["image_path"] = image_path
            scene["image_url"] = image_url
            scene["generation_metadata"] = {
                "provider": provider.get_provider_info()["name"],
                "model": provider.get_provider_info()["model"],
                "art_style": art_style_id,
                "reference_image": previous_image_url,
                "index": i,
                "succeeded": True,
            }
            
            successful_count += 1
            previous_image_url = image_url
            
            # Update job progress (reuse session from pipeline)
            db_session = state.get("_db")
            if db_session and story_id and story_id != "temp":
                try:
                    from app.db.crud import update_job_progress
                    progress_pct = ((i + 1) / len(scenes)) * 100
                    update_job_progress(
                        db_session, story_id,
                        progress=progress_pct,
                        detail=f"Generated illustration {i+1} of {len(scenes)}"
                    )
                except Exception as db_err:
                    logger.debug(f"Could not update illustration progress: {db_err}")
            
            logger.info(f"✅ Illustration {i+1}/{len(scenes)} completed: {image_path}")
            
        except Exception as img_error:
            # Log detailed error for THIS specific image
            logger.exception(f"❌ Failed to generate illustration {i+1}/{len(scenes)} (beat: {scene['beat_name']})")
            logger.error(f"   Error type: {type(img_error).__name__}")
            logger.error(f"   Error message: {str(img_error)}")
            logger.error(f"   Prompt length: {len(full_prompt)} chars")
            
            # Record failure in scene metadata
            scene["image_path"] = None
            scene["image_url"] = None
            scene["generation_metadata"] = {
                "provider": provider.get_provider_info()["name"],
                "index": i,
                "succeeded": False,
                "error": str(img_error),
                "error_type": type(img_error).__name__,
            }
            
            failed_count += 1
            errors.append({
                "index": i,
                "beat": scene['beat_name'],
                "error": str(img_error)
            })
            
            # IMPORTANT: Continue to next image (don't break loop)
            # Some failures are transient - next image might succeed
            continue
    
    # Build response based on results
    total = len(scenes)
    
    if successful_count == 0:
        logger.error(f"❌ Illustration generation: 0/{total} succeeded - complete failure")
        return {
            "scenes": scenes,  # All have null image_url
            "error": f"Illustration generation failed: {errors[0]['error'] if errors else 'Unknown error'}"
        }
    
    elif successful_count < total:
        logger.warning(f"⚠️ Illustration generation: {successful_count}/{total} succeeded - partial success")
        return {
            "scenes": scenes,  # Has partial image_url data
            "partial_illustrations": True,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "errors": errors,
            "error": f"Generated {successful_count} of {total} illustrations. {failed_count} failed."
        }
    
    else:
        logger.info(f"✅ Illustration generation: {total}/{total} succeeded - complete success")
        return {"scenes": scenes}
