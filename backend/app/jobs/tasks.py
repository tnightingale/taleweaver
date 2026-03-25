"""
Background tasks for story generation.

These run in the huey worker process, not in gunicorn. The worker process
has its own memory space, so story generation I/O (LLM calls, TTS, image
gen, audio stitching) doesn't affect API responsiveness.
"""
import asyncio
import logging
import time

from huey import crontab
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
        "user_id": params.get("user_id"),
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


@huey.periodic_task(crontab(minute="*/5"))
def backfill_missing_videos():
    """
    Periodic task: find illustrated stories without videos and generate them.

    Runs every 5 minutes. Uses _maybe_enqueue_video which checks all
    preconditions (illustrations exist, no in-progress job, etc.).
    """
    from pathlib import Path
    from app.db.database import SessionLocal
    from app.db.models import Story

    db = SessionLocal()
    try:
        stories = (
            db.query(Story)
            .filter(Story.has_illustrations == True, Story.scene_data.isnot(None))
            .all()
        )
        candidates = [
            s for s in stories
            if not s.video_path or not Path(s.video_path).exists()
        ]
        if candidates:
            enqueued = sum(1 for s in candidates if _maybe_enqueue_video(s.id))
            if enqueued:
                logger.info(f"Video backfill: enqueued {enqueued}/{len(candidates)} stories")
    except Exception as e:
        logger.error(f"Video backfill failed: {e}")
    finally:
        db.close()


def _maybe_enqueue_video(story_id: str) -> bool:
    """
    Enqueue video generation if the story is illustrated and has no video yet.

    Checks all preconditions (illustrations, audio, no existing video, no
    in-progress job) before enqueuing. Safe to call multiple times.

    Returns True if a video job was enqueued, False otherwise.
    """
    import uuid
    from pathlib import Path

    from app.db.crud import get_story_by_id, create_job_state
    from app.db.database import SessionLocal
    from app.db.models import JobState

    db = SessionLocal()
    try:
        story = get_story_by_id(db, story_id)
        if not story:
            return False

        if not story.has_illustrations or not story.scene_data:
            return False
        if not story.scene_data.get("scenes"):
            return False
        if not story.audio_path or not Path(story.audio_path).exists():
            return False

        # Already has video
        if story.video_path and Path(story.video_path).exists():
            return False

        # Check for in-progress video job
        existing = (
            db.query(JobState)
            .filter(
                JobState.short_id == story.short_id,
                JobState.status == "processing",
                JobState.current_stage == "generating_video",
            )
            .first()
        )
        if existing:
            return False

        video_job_id = str(uuid.uuid4())
        create_job_state(db, video_job_id, ["generating_video"])
        job_record = db.query(JobState).filter(JobState.job_id == video_job_id).first()
        if job_record:
            job_record.short_id = story.short_id
            db.commit()

        generate_video_task(video_job_id, story.short_id, story.id)
        logger.info(f"[{story_id}] Auto-enqueued video generation as job {video_job_id}")
        return True
    except Exception as e:
        logger.error(f"[{story_id}] Failed to auto-enqueue video: {e}")
        return False
    finally:
        db.close()


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

    # Auto-enqueue video generation for illustrated stories
    _maybe_enqueue_video(job_id)


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
                image_url = get_illustration_url(story_id, scene_idx) + f"?v={int(time.time())}"

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


@huey.task(retries=1, retry_delay=30)
def add_illustrations_task(
    job_id: str,
    short_id: str,
    story_id: str,
    art_style: str,
    custom_art_style_prompt: str = None,
):
    """
    Add illustrations to a story that has none.

    Runs scene analysis (LLM) to generate illustration prompts,
    then generates images for all scenes.
    """
    asyncio.run(
        _run_add_illustrations(job_id, short_id, story_id, art_style, custom_art_style_prompt)
    )


async def _run_add_illustrations(
    job_id: str,
    short_id: str,
    story_id: str,
    art_style: str,
    custom_art_style_prompt: str = None,
):
    """Async add-illustrations logic — runs scene analysis then illustration generation."""
    import yaml
    from pathlib import Path

    from app.db.crud import (
        get_story_by_short_id,
        update_job_progress,
        update_story_illustrations,
        mark_job_complete,
        mark_job_failed,
    )
    from app.db.database import SessionLocal
    from app.graph.nodes.scene_analyzer import scene_analyzer
    from app.graph.nodes.timestamp_calculator import timestamp_calculator
    from app.services.illustration.factory import get_illustration_provider
    from app.utils.storage import save_illustration, get_illustration_url

    DATA_DIR = Path(__file__).parent.parent / "data"
    with open(DATA_DIR / "art_styles.yaml") as f:
        art_styles = {style["id"]: style for style in yaml.safe_load(f)}

    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        if not story:
            mark_job_failed(db, job_id, f"Story {short_id} not found")
            return

        # Step 1: Run scene analysis
        update_job_progress(db, job_id, 5, "Analyzing story scenes...")

        analysis_state = {
            "art_style": art_style,
            "story_text": story.transcript,
            "title": story.title,
            "kid_name": story.kid_name,
            "kid_age": story.kid_age,
            "story_type": story.story_type,
        }
        analysis_result = await scene_analyzer(analysis_state)

        scenes = analysis_result.get("scenes")
        character_description = analysis_result.get("character_description", "")

        if not scenes:
            mark_job_failed(db, job_id, "Scene analysis failed — no scenes generated")
            return

        logger.info(f"[{job_id}] Scene analysis complete: {len(scenes)} scenes")

        # Step 2: Calculate timestamps
        ts_state = {"scenes": scenes, "duration_seconds": story.duration_seconds}
        ts_result = timestamp_calculator(ts_state)
        scenes = ts_result["scenes"]

        # Step 3: Resolve art style prompt
        if art_style == "custom":
            art_style_prompt = custom_art_style_prompt or ""
        else:
            art_style_data = art_styles.get(art_style)
            if not art_style_data or not art_style_data.get("prompt"):
                mark_job_failed(db, job_id, f"Unknown art style: {art_style}")
                return
            art_style_prompt = art_style_data["prompt"]

        # Step 4: Generate illustrations
        provider = get_illustration_provider()
        succeeded = 0

        for i, scene in enumerate(scenes):
            try:
                prompt = scene.get("illustration_prompt", "")
                if i == 0 and character_description:
                    prompt = f"{character_description}. {prompt}"

                image_bytes = await provider.generate_image(
                    prompt=prompt,
                    art_style=art_style_prompt,
                )

                image_path = save_illustration(story_id, i, image_bytes)
                image_url = get_illustration_url(story_id, i) + f"?v={int(time.time())}"

                scene["image_path"] = image_path
                scene["image_url"] = image_url
                scene["generation_metadata"] = {
                    "provider": provider.get_provider_info()["name"],
                    "model": provider.get_provider_info()["model"],
                    "art_style": art_style,
                    "index": i,
                    "succeeded": True,
                }
                succeeded += 1

            except Exception as e:
                logger.error(f"[{job_id}] Failed to generate scene {i}: {e}")
                scene["image_path"] = None
                scene["image_url"] = None
                scene["generation_metadata"] = {
                    "provider": provider.get_provider_info()["name"],
                    "index": i,
                    "succeeded": False,
                    "error": str(e),
                }

            progress = 10 + ((i + 1) / len(scenes)) * 85
            update_job_progress(
                db, job_id, progress,
                f"Generated {i + 1} of {len(scenes)} illustrations",
            )

        # Step 5: Build scene_data and update story
        scene_data = {
            "scenes": scenes,
            "art_style_prompt": art_style_prompt,
            "character_description": character_description,
        }

        update_story_illustrations(
            db, short_id, scene_data, art_style=art_style
        )

        if succeeded > 0:
            mark_job_complete(
                db, job_id,
                title=f"Added {succeeded}/{len(scenes)} illustrations",
                duration_seconds=0,
                transcript="",
                short_id=short_id,
            )
            logger.info(f"[{job_id}] Add illustrations complete: {succeeded}/{len(scenes)} succeeded")

            # Auto-enqueue video generation now that illustrations exist
            _maybe_enqueue_video(story_id)
        else:
            mark_job_failed(db, job_id, "All illustration generation attempts failed")

    except Exception as e:
        logger.error(f"[{job_id}] Add illustrations failed: {e}", exc_info=True)
        mark_job_failed(db, job_id, str(e))
    finally:
        db.close()


@huey.task(retries=1, retry_delay=30)
def generate_video_task(job_id: str, short_id: str, story_id: str):
    """
    Generate MP4 slideshow video from illustrations + audio.

    Combines scene PNGs with the audio MP3 into an H.264/AAC MP4
    suitable for AirPlay to Apple TV.
    """
    asyncio.run(_run_video_generation(job_id, short_id, story_id))


async def _run_video_generation(job_id: str, short_id: str, story_id: str):
    """Async video generation logic — runs in its own event loop."""
    from pathlib import Path

    from app.config import settings
    from app.db.crud import (
        get_story_by_short_id,
        update_job_progress,
        update_story_video_path,
        mark_job_complete,
        mark_job_failed,
    )
    from app.db.database import SessionLocal
    from app.utils.video_transcoder import generate_story_video

    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        if not story:
            mark_job_failed(db, job_id, f"Story {short_id} not found")
            return

        if not story.has_illustrations or not story.scene_data:
            mark_job_failed(db, job_id, "Story has no illustrations")
            return

        scenes = story.scene_data.get("scenes", [])
        if not scenes:
            mark_job_failed(db, job_id, "Story has no scene data")
            return

        audio_path = Path(story.audio_path)
        if not audio_path.exists():
            mark_job_failed(db, job_id, "Audio file not found")
            return

        story_dir = settings.storage_path / "stories" / story_id
        output_path = story_dir / "video.mp4"

        update_job_progress(db, job_id, 10, "Generating video...")

        await generate_story_video(
            story_dir=story_dir,
            scenes=scenes,
            audio_path=audio_path,
            output_path=output_path,
        )

        update_story_video_path(db, short_id, str(output_path))

        mark_job_complete(
            db, job_id,
            title="Video generated",
            duration_seconds=story.duration_seconds,
            transcript="",
            short_id=short_id,
        )
        logger.info(f"[{job_id}] Video generation complete for story {short_id}")

    except Exception as e:
        logger.error(f"[{job_id}] Video generation failed: {e}", exc_info=True)
        mark_job_failed(db, job_id, str(e))
    finally:
        db.close()
