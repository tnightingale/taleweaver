import logging
import time
import uuid
import json
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse

logger = logging.getLogger(__name__)

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.graph.pipeline import create_story_pipeline
from app.models.requests import CustomStoryRequest, HistoricalStoryRequest
from app.models.responses import JobCreatedResponse, JobStatusResponse, JobCompleteResponse

router = APIRouter(prefix="/api/story")

DATA_DIR = Path(__file__).parent.parent / "data"

# Job state is now stored in database (job_state table)
# This enables multi-worker support - all workers share the same job state
# See app/db/crud.py for job state CRUD functions


def _format_kid_details(kid) -> str:
    parts = []
    if kid.favorite_animal:
        parts.append(f"Favorite animal: {kid.favorite_animal}")
    if kid.favorite_color:
        parts.append(f"Favorite color: {kid.favorite_color}")
    if kid.hobby:
        parts.append(f"Hobby: {kid.hobby}")
    if kid.best_friend:
        parts.append(f"Best friend: {kid.best_friend}")
    if kid.pet_name:
        parts.append(f"Pet: {kid.pet_name}")
    if kid.personality:
        parts.append(f"Personality: {kid.personality}")
    return ". ".join(parts)


# Cache YAML data at module level
_events_cache: Optional[list] = None


def _load_events() -> list:
    global _events_cache
    if _events_cache is None:
        with open(DATA_DIR / "historical_events.yaml") as f:
            _events_cache = yaml.safe_load(f)
    return _events_cache


def _load_event(event_id: str) -> Optional[dict]:
    for event in _load_events():
        if event["id"] == event_id:
            return event
    return None


# Maps LangGraph node names to frontend stage names
NODE_TO_STAGE = {
    "story_writer": "writing",
    "scene_analyzer": "analyzing_scenes",
    "script_splitter": "splitting",
    "voice_synthesizer": "synthesizing",
    "illustration_generator": "generating_illustrations",
    "audio_stitcher": "stitching",
    "timestamp_calculator": "finalizing",
}
STAGE_ORDER = list(NODE_TO_STAGE.keys())


def _friendly_error(e: Exception) -> str:
    """Convert raw exceptions into user-friendly error messages."""
    msg = str(e).lower()
    if "quota_exceeded" in msg or "quota" in msg:
        return "ElevenLabs voice generation quota exceeded. Please upgrade your plan or wait for it to reset."
    if "invalid api key" in msg or "invalid_api_key" in msg:
        return "Invalid ElevenLabs API key. Please check your key in backend/.env."
    if "401" in msg and "elevenlabs" in msg:
        return "ElevenLabs authentication failed. Please check your API key or quota."
    if "rate_limit" in msg or "rate limit" in msg or "429" in msg:
        return "API rate limit reached. Please wait a moment and try again."
    if "timeout" in msg or "timed out" in msg:
        return "The request timed out. Please try again."
    if "anthropic" in msg or "openai" in msg or "groq" in msg:
        return "LLM provider error. Please check your API key and try again."
    return "Something unexpected went wrong. Check the server logs for details."


async def run_pipeline(job_id: str, state: dict):
    from app.db.crud import update_job_stage, mark_job_complete, mark_job_failed, save_story
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    
    try:
        # Pass db session through state so nodes can reuse it
        # This prevents creating 20+ new connections during generation
        state["_db"] = db
        
        pipeline = create_story_pipeline()

        logger.info(f"[{job_id}] Starting pipeline: type={state['story_type']}")
        update_job_stage(db, job_id, "writing")

        # Stream node-by-node to track progress
        final_state = None
        async for event in pipeline.astream(state):
            # event is {node_name: node_output_dict}
            for node_name in event:
                # After a node completes, advance to the next stage
                idx = STAGE_ORDER.index(node_name) if node_name in STAGE_ORDER else -1
                if idx + 1 < len(STAGE_ORDER):
                    next_stage = NODE_TO_STAGE[STAGE_ORDER[idx + 1]]
                    stage_progress = ((idx + 1) / len(STAGE_ORDER)) * 100
                    update_job_stage(db, job_id, next_stage, progress=stage_progress)
                    logger.info(f"[{job_id}] Stage: {next_stage} ({stage_progress:.0f}%)")
                # Merge node output into our tracked state
                if final_state is None:
                    final_state = {**state, **event[node_name]}
                else:
                    final_state.update(event[node_name])

        # Build scene_data for database
        scene_data = None
        if final_state.get("scenes"):
            scene_data = {
                "scenes": final_state["scenes"],
                "art_style_prompt": state.get("art_style"),
                "character_description": final_state.get("character_description"),
            }
        
        # Persist story to permanent storage
        try:
            db_story = save_story(
                db=db,
                story_id=job_id,
                title=final_state["title"],
                kid_name=state["kid_name"],
                kid_age=state["kid_age"],
                story_type=state["story_type"],
                genre=state.get("genre"),
                event_id=state.get("event_id"),
                mood=state.get("mood"),
                length=state.get("length"),
                transcript=final_state.get("story_text", ""),
                duration_seconds=final_state["duration_seconds"],
                audio_path=final_state.get("final_audio_path"),
                audio_bytes=final_state.get("final_audio"),
                art_style=state.get("art_style"),
                scene_data=scene_data,
                cover_image_path=final_state.get("cover_image_path"),
                user_id=state.get("user_id"),
            )
            short_id = db_story.short_id
            logger.info(f"[{job_id}] Story persisted with short_id={short_id}")
            
            # Mark job complete in job_state
            mark_job_complete(
                db,
                job_id,
                title=final_state["title"],
                duration_seconds=final_state["duration_seconds"],
                transcript=final_state.get("story_text", ""),
                short_id=short_id,
                art_style=state.get("art_style"),
                scenes=final_state.get("scenes"),
            )
            
        except Exception as persist_error:
            logger.error(f"[{job_id}] Failed to persist story: {persist_error}", exc_info=True)
            # Mark job as failed
            mark_job_failed(db, job_id, str(persist_error))
            raise  # Re-raise to trigger outer except

        logger.info(f"[{job_id}] Pipeline complete: title='{final_state['title']}', duration={final_state['duration_seconds']}s")
        
    except Exception as e:
        logger.error(f"[{job_id}] Pipeline failed: {e}", exc_info=True)
        mark_job_failed(db, job_id, _friendly_error(e))
    finally:
        db.close()


@router.post("/custom", response_model=JobCreatedResponse)
async def create_custom_story(request: CustomStoryRequest, user: User = Depends(get_current_user)):
    from app.db.crud import create_job_state, cleanup_old_jobs
    from app.db.database import SessionLocal
    
    # Cleanup old completed/failed jobs
    db = SessionLocal()
    try:
        cleanup_old_jobs(db, max_age_hours=24)
    finally:
        db.close()

    job_id = str(uuid.uuid4())
    
    # Determine stages based on whether illustrations are enabled
    if request.art_style:
        stages = ["writing", "analyzing_scenes", "splitting", "synthesizing", "generating_illustrations", "stitching", "finalizing"]
    else:
        stages = ["writing", "splitting", "synthesizing", "stitching"]
    
    # Only serializable params — no bytes, no db sessions
    story_params = {
        "kid_name": request.kid.name,
        "kid_age": request.kid.age,
        "kid_details": _format_kid_details(request.kid),
        "story_type": "custom",
        "genre": request.genre,
        "description": request.description,
        "event_id": None,
        "event_data": None,
        "mood": request.mood,
        "length": request.length,
        "art_style": request.art_style,
        "custom_art_style_prompt": request.custom_art_style_prompt,
        "user_id": user.id,
    }

    # Create job state in database (stores params for retry)
    db = SessionLocal()
    try:
        create_job_state(db, job_id, stages, story_params=story_params)
    finally:
        db.close()

    # Enqueue via huey background worker
    from app.jobs.tasks import generate_story_task
    generate_story_task(job_id, story_params)

    return JobCreatedResponse(
        job_id=job_id,
        status="processing",
        stages=stages,
        current_stage="writing",
    )


@router.post("/historical", response_model=JobCreatedResponse)
async def create_historical_story(request: HistoricalStoryRequest, user: User = Depends(get_current_user)):
    from app.db.crud import create_job_state, cleanup_old_jobs
    from app.db.database import SessionLocal
    
    event_data = _load_event(request.event_id)
    if not event_data:
        raise HTTPException(status_code=404, detail=f"Event '{request.event_id}' not found")

    # Cleanup old completed/failed jobs
    db = SessionLocal()
    try:
        cleanup_old_jobs(db, max_age_hours=24)
    finally:
        db.close()

    job_id = str(uuid.uuid4())
    
    # Determine stages based on whether illustrations are enabled
    if request.art_style:
        stages = ["writing", "analyzing_scenes", "splitting", "synthesizing", "generating_illustrations", "stitching", "finalizing"]
    else:
        stages = ["writing", "splitting", "synthesizing", "stitching"]
    
    story_params = {
        "kid_name": request.kid.name,
        "kid_age": request.kid.age,
        "kid_details": _format_kid_details(request.kid),
        "story_type": "historical",
        "genre": None,
        "description": None,
        "event_id": request.event_id,
        "event_data": event_data,
        "mood": request.mood,
        "length": request.length,
        "art_style": request.art_style,
        "custom_art_style_prompt": request.custom_art_style_prompt,
        "user_id": user.id,
    }

    # Create job state in database (stores params for retry)
    db = SessionLocal()
    try:
        create_job_state(db, job_id, stages, story_params=story_params)
    finally:
        db.close()

    # Enqueue via huey background worker
    from app.jobs.tasks import generate_story_task
    generate_story_task(job_id, story_params)

    return JobCreatedResponse(
        job_id=job_id,
        status="processing",
        stages=stages,
        current_stage="writing",
    )


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    from app.db.crud import get_job_state
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        job = get_job_state(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status == "complete":
            short_id = job.short_id or ""
            
            # Build scenes response if illustrations exist
            scenes = None
            if job.scenes_json:
                from app.models.responses import SceneResponse
                scenes_data = json.loads(job.scenes_json)
                scenes = [
                    SceneResponse(
                        beat_index=s["beat_index"],
                        beat_name=s["beat_name"],
                        text_excerpt=s["text_excerpt"],
                        timestamp_start=s["timestamp_start"],
                        timestamp_end=s["timestamp_end"],
                        image_url=s.get("image_url")
                    )
                    for s in scenes_data
                ]
            
            return JobCompleteResponse(
                job_id=job_id,
                status="complete",
                title=job.title,
                duration_seconds=job.duration_seconds,
                audio_url=f"/api/story/audio/{job_id}",
                transcript=job.transcript or "",
                short_id=short_id,
                permalink=f"/s/{short_id}" if short_id else "",
                has_illustrations=bool(job.scenes_json),
                art_style=job.art_style,
                scenes=scenes,
            )

        # Parse partial progress if available
        partial_progress = None
        if job.partial_data_json:
            from app.models.responses import PartialProgress
            partial_data = json.loads(job.partial_data_json)
            partial_progress = PartialProgress(
                segments_completed=partial_data.get("segments_completed"),
                segments_total=partial_data.get("segments_total"),
                checkpoint_node=partial_data.get("checkpoint_node")
            )
        
        return JobStatusResponse(
            job_id=job_id,
            status=job.status,
            current_stage=job.current_stage or "",
            progress=int(job.progress or 0),
            total_segments=0,  # Deprecated field
            error=job.error_message or "",
            resumable=job.resumable,
            partial_progress=partial_progress,
            retry_count=job.retry_count,
        )
    finally:
        db.close()


@router.get("/audio/{job_id}")
async def get_audio(job_id: str, download: bool = False):
    """
    Get audio for completed job (streams from saved file).
    Note: Audio is saved to filesystem when story completes.
    """
    from app.db.crud import get_story_by_id
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        # job_id is the same as story_id
        story = get_story_by_id(db, job_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found or not yet complete")
        
        audio_path = Path(story.audio_path)
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        disposition = "attachment" if download else "inline"
        return FileResponse(
            path=audio_path,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f'{disposition}; filename="story.mp3"'},
        )
    finally:
        db.close()


@router.post("/retry/{job_id}")
async def retry_job(job_id: str):
    """
    Resume a failed job from last checkpoint.
    
    Only works for jobs marked as resumable (quota/rate limit errors).
    """
    from app.db.crud import get_job_state
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        job = get_job_state(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status not in ["failed"]:
            raise HTTPException(status_code=400, detail="Job is not in a failed state")
        
        if not job.resumable:
            raise HTTPException(status_code=400, detail="Job cannot be resumed (permanent error)")

        if job.retry_count >= 3:
            raise HTTPException(status_code=400, detail="Maximum retry limit reached (3 attempts)")

        if not job.story_params_json:
            raise HTTPException(
                status_code=400,
                detail="Job cannot be retried (no stored parameters — legacy job)"
            )

        # Update retry count and status, reset progress
        job.retry_count += 1
        job.status = "processing"
        job.error_message = None
        job.progress = 0
        job.progress_detail = ""
        db.commit()

        # Re-enqueue via huey with stored params
        from app.jobs.tasks import generate_story_task
        story_params = json.loads(job.story_params_json)
        generate_story_task(job_id, story_params)

        logger.info(f"Job {job_id} re-enqueued via huey (retry {job.retry_count}/3)")

        return {"job_id": job_id, "status": "resuming", "retry_count": job.retry_count}
        
    finally:
        db.close()


