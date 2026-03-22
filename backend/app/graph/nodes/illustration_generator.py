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
    
    try:
        provider = get_illustration_provider()
        logger.info(f"Using provider: {provider.get_provider_info()['name']}")
        
        # We need a job_id or story_id to save images
        # Since we don't have final story ID yet, use a temp identifier
        # The pipeline should have a job_id in state
        story_id = state.get("job_id", "temp")
        
        previous_image_url = None
        
        for i, scene in enumerate(scenes):
            logger.info(f"Generating illustration {i+1}/{len(scenes)}: {scene['beat_name']}")
            
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
            
            # Update scene metadata
            scene["image_path"] = image_path
            scene["image_url"] = image_url
            scene["generation_metadata"] = {
                "provider": provider.get_provider_info()["name"],
                "model": provider.get_provider_info()["model"],
                "art_style": art_style_id,
                "reference_image": previous_image_url,
            }
            
            # Use this image as reference for next scene
            previous_image_url = image_url
            
            logger.info(f"Illustration {i+1} generated and saved: {image_path}")
        
        logger.info(f"All {len(scenes)} illustrations generated successfully")
        return {"scenes": scenes}
        
    except Exception as e:
        logger.error(f"Illustration generation failed: {e}")
        # Return scenes without images - graceful degradation
        return {"scenes": scenes, "error": f"Illustration generation failed: {str(e)}"}
