import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse

from fastapi import Depends

from app.routes.config import router as config_router
from app.routes.story import router as story_router
from app.routes.auth import router as auth_router
from app.models.responses import StoryResponse, StoriesListResponse
from app.models.requests import UpdateStoryTitleRequest, RegenerateIllustrationsRequest
from app.auth.dependencies import get_current_user, verify_story_ownership
from app.db.models import User

app = FastAPI(title="Taleweaver")

# CORS: when credentials are used (cookie-based auth), origins must be explicit.
# Set CORS_ORIGINS env var to a comma-separated list of allowed origins.
# Without it, CORS is disabled (same-origin only, which is the production default
# since Caddy serves both frontend and API on the same origin).
from app.config import settings as _settings
_cors_origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()] if _settings.cors_origins else []
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router)
app.include_router(config_router)
app.include_router(story_router)

# Jobs endpoint (at /api/jobs/recent, not under /api/story)
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.db.models import JobState

_last_orphan_check: Optional[datetime] = None

@app.get("/api/jobs/recent")
async def get_recent_jobs(user: User = Depends(get_current_user)):
    """Get jobs from last 24 hours for navigation persistence"""
    global _last_orphan_check
    from sqlalchemy.exc import OperationalError

    db = SessionLocal()
    try:
        # Periodically recover orphaned jobs (at most once per minute).
        # This catches jobs left in "processing" after a deploy or crash,
        # even if the startup check ran too early to detect them.
        now = datetime.utcnow()
        if _last_orphan_check is None or (now - _last_orphan_check).total_seconds() >= 60:
            from app.db.crud import recover_orphaned_jobs
            recovered = recover_orphaned_jobs(db, stale_minutes=5)
            if recovered:
                logger = logging.getLogger(__name__)
                logger.warning(f"Recovered {recovered} orphaned job(s) during periodic check")
            _last_orphan_check = now

        cutoff = now - timedelta(hours=24)
        jobs = db.query(JobState).filter(
            JobState.created_at > cutoff,
            JobState.user_id == user.id,
        ).order_by(JobState.created_at.desc()).limit(20).all()

        return {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "current_stage": job.current_stage,
                    "progress": job.progress or 0,
                    "title": job.title,
                    "created_at": job.created_at.isoformat() + 'Z',
                    "error": job.error_message if job.status == "failed" else None
                }
                for job in jobs
            ]
        }
    except OperationalError:
        # Table doesn't exist yet (during tests or fresh deployment)
        return {"jobs": []}
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    """Log configuration status on startup."""
    from app.config import settings
    from app.db.database import init_db
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Taleweaver Starting")
    logger.info("=" * 60)
    
    # Initialize database
    try:
        # Import models to register them with Base.metadata before calling init_db()
        from app.db import models  # noqa: F401 - Ensure models are loaded
        init_db()
        logger.info("Database initialized successfully")

        # Run migrations to add any missing columns/tables
        from app.db.migrate import run_migrations
        run_migrations()

        # Recover any jobs orphaned by a previous crash/restart
        from app.db.crud import recover_orphaned_jobs
        db = SessionLocal()
        try:
            recovered = recover_orphaned_jobs(db, stale_minutes=5)
            if recovered:
                logger.warning(f"Recovered {recovered} orphaned job(s) from previous crash")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Check LLM configuration
    llm_configured = False
    if settings.llm_provider == "groq":
        llm_configured = bool(settings.groq_api_key)
        logger.info(f"LLM Provider: Groq {'✓' if llm_configured else '✗ (NO API KEY)'}")
    elif settings.llm_provider == "anthropic":
        llm_configured = bool(settings.anthropic_api_key)
        logger.info(f"LLM Provider: Anthropic {'✓' if llm_configured else '✗ (NO API KEY)'}")
    elif settings.llm_provider == "openai":
        llm_configured = bool(settings.openai_api_key)
        logger.info(f"LLM Provider: OpenAI {'✓' if llm_configured else '✗ (NO API KEY)'}")
    else:
        logger.warning(f"Unknown LLM provider: {settings.llm_provider}")
    
    # Check TTS configuration  
    tts_configured = bool(settings.elevenlabs_api_key)
    logger.info(f"ElevenLabs TTS: {'✓' if tts_configured else '✗ (NO API KEY)'}")
    
    # Overall status
    if llm_configured and tts_configured:
        logger.info("✓ Application fully configured and ready!")
    else:
        logger.warning("⚠ Application running but NOT CONFIGURED - stories cannot be generated")
        logger.warning("  Set environment variables: LLM_PROVIDER, *_API_KEY, ELEVENLABS_API_KEY")
    
    logger.info("=" * 60)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/up")
async def health_check():
    """Health check endpoint required by Once deployment platform."""
    return {"status": "ok"}


@app.get("/api/status")
async def status(_user: User = Depends(get_current_user)):
    """Application status including configuration state."""
    from app.config import settings
    
    has_llm = bool(
        (settings.llm_provider == "groq" and settings.groq_api_key) or
        (settings.llm_provider == "anthropic" and settings.anthropic_api_key) or
        (settings.llm_provider == "openai" and settings.openai_api_key)
    )
    has_tts = bool(settings.elevenlabs_api_key)
    
    return {
        "status": "running",
        "configured": has_llm and has_tts,
        "llm_configured": has_llm,
        "llm_provider": settings.llm_provider,
        "tts_configured": has_tts,
        "ready": has_llm and has_tts,
    }


def _get_video_url(story) -> Optional[str]:
    """Get video URL if a generated MP4 exists for this story."""
    if getattr(story, "video_path", None) and Path(story.video_path).exists():
        return f"/api/permalink/{story.short_id}/video"
    return None


def _get_cover_image_url(story) -> Optional[str]:
    """Get cover image URL: prefer dedicated cover, fall back to first scene image."""
    if getattr(story, "cover_image_path", None):
        return f"/storage/stories/{story.id}/cover.png"
    if story.has_illustrations and story.scene_data:
        scenes = story.scene_data.get("scenes", [])
        if scenes and scenes[0].get("image_url"):
            return scenes[0]["image_url"]
    return None


# Permalink API routes (under /api for clarity)
@app.get("/api/permalink/{short_id}", response_model=StoryResponse)
async def get_story_permalink(short_id: str):
    """Get story metadata by compact short ID"""
    from app.db.crud import get_story_by_short_id
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        # Build scenes response if illustrations exist
        scenes = None
        if story.has_illustrations and story.scene_data:
            from app.models.responses import SceneResponse
            scenes = [
                SceneResponse(
                    beat_index=s["beat_index"],
                    beat_name=s["beat_name"],
                    text_excerpt=s["text_excerpt"],
                    timestamp_start=s["timestamp_start"],
                    timestamp_end=s["timestamp_end"],
                    image_url=s.get("image_url")
                )
                for s in story.scene_data.get("scenes", [])
            ]
        
        response = StoryResponse(
            id=story.id,
            short_id=story.short_id,
            title=story.title,
            kid_name=story.kid_name,
            kid_age=story.kid_age,
            story_type=story.story_type,
            genre=story.genre,
            event_id=story.event_id,
            transcript=story.transcript,
            duration_seconds=story.duration_seconds,
            created_at=story.created_at.isoformat() + 'Z',  # Append Z to indicate UTC
            permalink=f"/s/{story.short_id}",
            audio_url=f"/api/permalink/{story.short_id}/audio",
            has_illustrations=story.has_illustrations,
            art_style=story.art_style,
            scenes=scenes,
            cover_image_url=_get_cover_image_url(story),
            video_url=_get_video_url(story),
        )
        return Response(
            content=response.model_dump_json(),
            media_type="application/json",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    finally:
        db.close()


@app.get("/api/permalink/{short_id}/audio")
async def get_story_audio_permalink(short_id: str):
    """Stream audio by compact short ID (efficient file streaming)"""
    from app.db.crud import get_story_by_short_id
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    story = get_story_by_short_id(db, short_id)
    db.close()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    audio_path = Path(story.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Use FileResponse for efficient streaming (doesn't load entire file into memory)
    # Sanitize filename for safety
    safe_filename = "".join(c for c in story.title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_filename = safe_filename or "story"
    
    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=f"{safe_filename}.mp3",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@app.get("/api/permalink/{short_id}/video")
async def get_story_video_permalink(short_id: str):
    """Stream video by compact short ID (for AirPlay)"""
    from app.db.crud import get_story_by_short_id
    from app.db.database import SessionLocal

    db = SessionLocal()
    story = get_story_by_short_id(db, short_id)
    db.close()

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if not story.video_path:
        raise HTTPException(status_code=404, detail="Video not generated yet")

    video_path = Path(story.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Disposition": "inline",
        },
    )


@app.post("/api/stories/{short_id}/video")
async def generate_story_video_endpoint(
    short_id: str, user: User = Depends(get_current_user)
):
    """Trigger video generation for an illustrated story, or return cached URL."""
    import uuid
    from app.db.crud import get_story_by_short_id, create_job_state
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        verify_story_ownership(story, user)

        if not story.has_illustrations or not story.scene_data:
            raise HTTPException(
                status_code=400, detail="Story has no illustrations"
            )

        # If video already exists, return immediately
        if story.video_path and Path(story.video_path).exists():
            return {
                "status": "complete",
                "video_url": f"/api/permalink/{story.short_id}/video",
            }

        # Check for existing in-progress video generation job
        existing = (
            db.query(JobState)
            .filter(
                JobState.short_id == short_id,
                JobState.status == "processing",
                JobState.current_stage == "generating_video",
            )
            .first()
        )
        if existing:
            return {"job_id": existing.job_id, "status": "processing"}

        # Create job and enqueue
        job_id = str(uuid.uuid4())
        create_job_state(
            db, job_id, ["generating_video"],
            story_params={"user_id": user.id},
        )

        # Set short_id on the job so we can detect duplicates
        job = db.query(JobState).filter(JobState.job_id == job_id).first()
        if job:
            job.short_id = short_id
            db.commit()

        from app.jobs.tasks import generate_video_task
        generate_video_task(job_id, story.short_id, story.id)

        return {"job_id": job_id, "status": "processing"}
    finally:
        db.close()


# Library routes
@app.get("/api/stories", response_model=StoriesListResponse)
async def list_all_stories(
    kid_name: Optional[str] = None,
    story_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "created_desc",
    user: User = Depends(get_current_user),
):
    """List stories with optional filters and pagination (scoped to current user)"""
    from app.db.crud import list_stories
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        stories, total = list_stories(
            db=db,
            kid_name=kid_name,
            story_type=story_type,
            user_id=user.id,
            limit=limit,
            offset=offset,
            sort=sort
        )
        
        from app.models.responses import SceneResponse

        story_responses = []
        for story in stories:
            scenes = None
            if story.has_illustrations and story.scene_data:
                scenes = [
                    SceneResponse(
                        beat_index=s["beat_index"],
                        beat_name=s["beat_name"],
                        text_excerpt=s["text_excerpt"],
                        timestamp_start=s["timestamp_start"],
                        timestamp_end=s["timestamp_end"],
                        image_url=s.get("image_url")
                    )
                    for s in story.scene_data.get("scenes", [])
                ]

            story_responses.append(
                StoryResponse(
                    id=story.id,
                    short_id=story.short_id,
                    title=story.title,
                    kid_name=story.kid_name,
                    kid_age=story.kid_age,
                    story_type=story.story_type,
                    genre=story.genre,
                    event_id=story.event_id,
                    transcript=story.transcript,
                    duration_seconds=story.duration_seconds,
                    created_at=story.created_at.isoformat() + 'Z',
                    permalink=f"/s/{story.short_id}",
                    audio_url=f"/api/permalink/{story.short_id}/audio",
                    has_illustrations=story.has_illustrations,
                    art_style=story.art_style,
                    scenes=scenes,
                    cover_image_url=_get_cover_image_url(story),
                    video_url=_get_video_url(story),
                )
            )
        
        has_more = (offset + len(stories)) < total
        
        return StoriesListResponse(
            stories=story_responses,
            total=total,
            has_more=has_more
        )
    finally:
        db.close()


@app.delete("/api/stories/{short_id}", status_code=204)
async def delete_story_endpoint(short_id: str, user: User = Depends(get_current_user)):
    """Delete story by short ID (requires ownership)"""
    from app.db.crud import delete_story, get_story_by_short_id
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        verify_story_ownership(story, user)
        delete_story(db, short_id)
        return None  # 204 No Content
    finally:
        db.close()


@app.patch("/api/stories/{short_id}", response_model=StoryResponse)
async def update_story_title_endpoint(
    short_id: str, request: UpdateStoryTitleRequest, user: User = Depends(get_current_user)
):
    """Update story title (requires ownership)"""
    from app.db.crud import update_story_title, get_story_by_short_id
    from app.db.database import SessionLocal

    if not request.title or not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        verify_story_ownership(story, user)
        story = update_story_title(db, short_id, request.title.strip())
        
        return StoryResponse(
            id=story.id,
            short_id=story.short_id,
            title=story.title,
            kid_name=story.kid_name,
            kid_age=story.kid_age,
            story_type=story.story_type,
            genre=story.genre,
            event_id=story.event_id,
            transcript=story.transcript,
            duration_seconds=story.duration_seconds,
            created_at=story.created_at.isoformat() + 'Z',  # Append Z to indicate UTC
            permalink=f"/s/{story.short_id}",
            audio_url=f"/api/permalink/{story.short_id}/audio",
        )
    finally:
        db.close()


@app.post("/api/stories/{short_id}/regenerate-illustrations")
async def regenerate_illustrations_endpoint(
    short_id: str,
    request: Optional[RegenerateIllustrationsRequest] = None,
    user: User = Depends(get_current_user),
):
    """
    Manage illustrations for an existing story.

    Modes:
    - "missing" (default): Regenerate only failed/missing illustrations
    - "single": Regenerate a specific scene by index
    - "all": Regenerate all illustrations (optionally with a new art style)
    - "add": Add illustrations to a story that has none
    """
    import uuid
    from app.db.crud import get_story_by_short_id, create_job_state
    from app.db.database import SessionLocal

    logger = logging.getLogger(__name__)

    mode = request.mode if request else "missing"
    valid_modes = ("missing", "single", "all", "add")
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {mode}. Must be one of: {', '.join(valid_modes)}",
        )

    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        verify_story_ownership(story, user)

        # ── mode="add": add illustrations to a story that has none ──
        if mode == "add":
            if story.scene_data and story.scene_data.get("scenes"):
                raise HTTPException(
                    status_code=400,
                    detail="Story already has illustrations — use mode='all' to regenerate",
                )
            if not request or not request.art_style:
                raise HTTPException(
                    status_code=400,
                    detail="art_style is required when adding illustrations",
                )

            job_id = str(uuid.uuid4())
            stages = ["analyzing_scenes", "generating_illustrations"]
            create_job_state(db, job_id, stages)

            from app.jobs.tasks import add_illustrations_task
            add_illustrations_task(
                job_id,
                story.short_id,
                story.id,
                request.art_style,
                request.custom_art_style_prompt,
            )

            logger.info(
                f"[{job_id}] Add illustrations queued for story {short_id} "
                f"(style: {request.art_style})"
            )

            return {
                "job_id": job_id,
                "status": "processing",
                "story_id": story.id,
                "failed_count": 0,
                "total_scenes": 0,
            }

        # All other modes require existing art_style and scene_data
        if not story.art_style:
            raise HTTPException(
                status_code=400,
                detail="Story has no art style — use mode='add' to add illustrations",
            )

        if not story.scene_data or not story.scene_data.get("scenes"):
            raise HTTPException(
                status_code=400,
                detail="Story has no scene data — use mode='add' to add illustrations",
            )

        scenes = story.scene_data["scenes"]

        # ── mode="single": regenerate one specific scene ──
        if mode == "single":
            if request is None or request.scene_index is None:
                raise HTTPException(
                    status_code=400,
                    detail="scene_index is required for mode='single'",
                )
            if request.scene_index < 0 or request.scene_index >= len(scenes):
                raise HTTPException(
                    status_code=400,
                    detail=f"scene_index {request.scene_index} out of range (0-{len(scenes) - 1})",
                )
            target_indices = [request.scene_index]

        # ── mode="all": regenerate every scene ──
        elif mode == "all":
            target_indices = list(range(len(scenes)))

        # ── mode="missing": only failed/missing scenes ──
        else:
            target_indices = [
                i for i, s in enumerate(scenes)
                if not s.get("image_url")
                or (s.get("generation_metadata", {}) or {}).get("succeeded") is False
            ]
            if not target_indices:
                return {"status": "ok", "message": "All illustrations already present"}

        # Determine art style to use
        art_style = story.art_style
        if mode == "all" and request and request.art_style:
            art_style = request.art_style

        job_id = str(uuid.uuid4())
        stages = ["generating_illustrations"]
        create_job_state(db, job_id, stages)

        from app.jobs.tasks import regenerate_illustrations_task
        regenerate_illustrations_task(
            job_id,
            story.short_id,
            story.id,
            art_style,
            story.scene_data,
            target_indices,
        )

        logger.info(
            f"[{job_id}] Regeneration queued for story {short_id} (mode={mode}): "
            f"{len(target_indices)}/{len(scenes)} scenes"
        )

        return {
            "job_id": job_id,
            "status": "processing",
            "story_id": story.id,
            "failed_count": len(target_indices),
            "total_scenes": len(scenes),
        }
    finally:
        db.close()
