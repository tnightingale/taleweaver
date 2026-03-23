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
