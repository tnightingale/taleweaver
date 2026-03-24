"""
Background tasks for story generation.

These run in the huey worker process, not in gunicorn. The worker process
has its own memory space, so story generation I/O (LLM calls, TTS, image
gen, audio stitching) doesn't affect API responsiveness.
"""
import asyncio
import logging

from app.jobs.huey_app import huey

logger = logging.getLogger(__name__)


def build_state_from_params(job_id: str, params: dict) -> dict:
    """
    Reconstruct a full pipeline state dict from serializable parameters.

    The API route extracts only JSON-serializable fields into `params`.
    This function adds back the pipeline output placeholders that
    run_pipeline() and the LangGraph nodes expect.
    """
    return {
        "job_id": job_id,
        "kid_name": params["kid_name"],
        "kid_age": params["kid_age"],
        "kid_details": params.get("kid_details", ""),
        "story_type": params["story_type"],
        "genre": params.get("genre"),
        "description": params.get("description"),
        "event_id": params.get("event_id"),
        "event_data": params.get("event_data"),
        "mood": params.get("mood"),
        "length": params.get("length"),
        "art_style": params.get("art_style"),
        "custom_art_style_prompt": params.get("custom_art_style_prompt"),
        # Pipeline output placeholders
        "story_text": "",
        "title": "",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "final_audio_path": None,
        "duration_seconds": 0,
        "error": None,
        "scenes": None,
        "character_description": None,
    }


@huey.task(retries=2, retry_delay=60)
def generate_story_task(job_id: str, story_params: dict):
    """
    Run the full story generation pipeline in the huey worker process.

    Uses asyncio.run() to bridge from huey's synchronous worker to the
    async LangGraph pipeline. Each task invocation gets its own event loop.
    """
    from app.routes.story import run_pipeline

    logger.info(f"[{job_id}] huey worker starting pipeline")
    state = build_state_from_params(job_id, story_params)
    asyncio.run(run_pipeline(job_id, state))
    logger.info(f"[{job_id}] huey worker pipeline complete")


@huey.task(retries=1, retry_delay=30)
def regenerate_illustrations_task(
    job_id: str,
    short_id: str,
    story_id: str,
    art_style: str,
    scene_data: dict,
    failed_indices: list,
):
    """
    Re-run illustration generation for specific failed scenes.

    Only generates images for scenes at failed_indices — scenes that
    already have successful images are left untouched.
    """
    asyncio.run(
        _run_regeneration(job_id, short_id, story_id, art_style, scene_data, failed_indices)
    )


async def _run_regeneration(
    job_id: str,
    short_id: str,
    story_id: str,
    art_style: str,
    scene_data: dict,
    failed_indices: list,
):
    """Async regeneration logic — runs in its own event loop."""
    import yaml
    from pathlib import Path

    from app.db.crud import (
        update_job_progress,
        update_story_illustrations,
        mark_job_complete,
        mark_job_failed,
    )
    from app.db.database import SessionLocal
    from app.services.illustration.factory import get_illustration_provider
    from app.utils.storage import save_illustration, get_illustration_url

    DATA_DIR = Path(__file__).parent.parent / "data"
    with open(DATA_DIR / "art_styles.yaml") as f:
        art_styles = {style["id"]: style for style in yaml.safe_load(f)}

    db = SessionLocal()
    try:
        scenes = scene_data["scenes"]

        # Resolve art style prompt
        if art_style == "custom":
            art_style_prompt = scene_data.get("art_style_prompt", "")
        else:
            art_style_data = art_styles.get(art_style)
            if not art_style_data or not art_style_data.get("prompt"):
                mark_job_failed(db, job_id, f"Unknown art style: {art_style}")
                return
            art_style_prompt = art_style_data["prompt"]

        provider = get_illustration_provider()
        logger.info(
            f"[{job_id}] Regenerating {len(failed_indices)} illustrations "
            f"for story {short_id}"
        )

        succeeded = 0
        for step, scene_idx in enumerate(failed_indices):
            scene = scenes[scene_idx]
            try:
                char_desc = scene_data.get("character_description", "")
                prompt = scene.get("illustration_prompt", "")
                if scene_idx == 0 and char_desc:
                    prompt = f"{char_desc}. {prompt}"

                image_bytes = await provider.generate_image(
                    prompt=prompt,
                    art_style=art_style_prompt,
                )

                image_path = save_illustration(story_id, scene_idx, image_bytes)
                image_url = get_illustration_url(story_id, scene_idx)

                scene["image_path"] = image_path
                scene["image_url"] = image_url
                scene["generation_metadata"] = {
                    "provider": provider.get_provider_info()["name"],
                    "model": provider.get_provider_info()["model"],
                    "art_style": art_style,
                    "index": scene_idx,
                    "succeeded": True,
                    "regenerated": True,
                }
                succeeded += 1
                logger.info(f"[{job_id}] Regenerated scene {scene_idx} ({step + 1}/{len(failed_indices)})")

            except Exception as e:
                logger.error(f"[{job_id}] Failed to regenerate scene {scene_idx}: {e}")
                scene["generation_metadata"] = {
                    "provider": provider.get_provider_info()["name"],
                    "index": scene_idx,
                    "succeeded": False,
                    "error": str(e),
                    "regenerated": True,
                }

            progress = ((step + 1) / len(failed_indices)) * 100
            update_job_progress(
                db, job_id, progress,
                f"Regenerated {step + 1} of {len(failed_indices)} illustrations",
            )

        # Update the story record with new scene data
        update_story_illustrations(db, short_id, scene_data)

        if succeeded > 0:
            mark_job_complete(
                db, job_id,
                title=f"Regenerated {succeeded}/{len(failed_indices)} illustrations",
                duration_seconds=0,
                transcript="",
                short_id=short_id,
            )
            logger.info(f"[{job_id}] Regeneration complete: {succeeded}/{len(failed_indices)} succeeded")
        else:
            mark_job_failed(db, job_id, "All illustration regeneration attempts failed")

    except Exception as e:
        logger.error(f"[{job_id}] Regeneration failed: {e}", exc_info=True)
        mark_job_failed(db, job_id, str(e))
    finally:
        db.close()
