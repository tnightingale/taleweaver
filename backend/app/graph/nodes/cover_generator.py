"""
Cover Image Generator Node - Generates a dedicated cover/thumbnail image for the story
"""
import logging
import yaml
from pathlib import Path

from app.graph.state import StoryState
from app.services.illustration.factory import get_illustration_provider
from app.utils.storage import save_cover_image

logger = logging.getLogger(__name__)

# Load art styles data
DATA_DIR = Path(__file__).parent.parent.parent / "data"
with open(DATA_DIR / "art_styles.yaml") as f:
    ART_STYLES = {style["id"]: style for style in yaml.safe_load(f)}


async def cover_generator(state: StoryState) -> dict:
    """
    Generate a dedicated cover image for the story.

    Runs in parallel with voice_synthesizer and illustration_generator.
    Produces a single "book cover" style image optimized for library thumbnails.

    Returns:
        dict with 'cover_image_path' if successful
    """
    if not state.get("art_style"):
        logger.info("Skipping cover generation (no art style)")
        return {}

    art_style_id = state["art_style"]

    # Get art style prompt
    if art_style_id == "custom":
        art_style_prompt = state.get("custom_art_style_prompt", "")
    else:
        art_style_data = ART_STYLES.get(art_style_id)
        if not art_style_data or not art_style_data.get("prompt"):
            logger.error(f"Unknown or invalid art style: {art_style_id}")
            return {}
        art_style_prompt = art_style_data["prompt"]

    story_id = state.get("job_id", "temp")
    title = state.get("title", "A Story")
    char_desc = state.get("character_description", "")
    genre = state.get("genre", "")
    mood = state.get("mood", "")

    # Build a cover-specific prompt
    prompt_parts = [
        f"Children's book cover illustration for a story called \"{title}\".",
    ]
    if char_desc:
        prompt_parts.append(f"Main character: {char_desc}.")
    if genre:
        prompt_parts.append(f"Genre: {genre}.")
    if mood:
        prompt_parts.append(f"Mood: {mood}.")
    prompt_parts.append(
        "The image should be inviting, colorful, and capture the essence of the story. "
        "Suitable as a book cover or thumbnail. No text in the image."
    )
    full_prompt = " ".join(prompt_parts)

    logger.info(f"Generating cover image for story: {title}")

    try:
        provider = get_illustration_provider()
        image_bytes = await provider.generate_image(
            prompt=full_prompt,
            art_style=art_style_prompt,
            reference_image_url=None,
            aspect_ratio="3:2",
            resolution="2K",
        )

        image_path = save_cover_image(story_id, image_bytes)
        logger.info(f"Cover image generated: {image_path}")

        return {"cover_image_path": image_path}

    except Exception as e:
        logger.error(f"Cover generation failed: {e}")
        # Non-fatal — story continues without dedicated cover
        return {}
