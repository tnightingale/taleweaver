import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.routes.config import router as config_router
from app.routes.story import router as story_router
from app.models.responses import StoryResponse, StoriesListResponse

app = FastAPI(title="Taleweaver")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router)
app.include_router(story_router)


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
        init_db()
        logger.info("Database initialized successfully")
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
async def status():
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


# Permalink routes (root level for clean sharing URLs)
@app.get("/s/{short_id}", response_model=StoryResponse)
async def get_story_permalink(short_id: str):
    """Get story metadata by compact short ID"""
    from app.db.crud import get_story_by_short_id
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
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
            created_at=story.created_at.isoformat(),
            permalink=f"/s/{story.short_id}",
            audio_url=f"/s/{story.short_id}/audio",
        )
    finally:
        db.close()


@app.get("/s/{short_id}/audio")
async def get_story_audio_permalink(short_id: str):
    """Stream audio by compact short ID"""
    from app.db.crud import get_story_by_short_id
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        audio_path = Path(story.audio_path)
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        audio_bytes = audio_path.read_bytes()
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="{story.title}.mp3"',
                "Content-Length": str(len(audio_bytes)),
                "Accept-Ranges": "bytes",
            },
        )
    finally:
        db.close()


# Library routes
@app.get("/api/stories", response_model=StoriesListResponse)
async def list_all_stories(
    kid_name: Optional[str] = None,
    story_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort: str = "created_desc"
):
    """List stories with optional filters and pagination"""
    from app.db.crud import list_stories
    from app.db.database import SessionLocal
    
    db = SessionLocal()
    try:
        stories, total = list_stories(
            db=db,
            kid_name=kid_name,
            story_type=story_type,
            limit=limit,
            offset=offset,
            sort=sort
        )
        
        story_responses = [
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
                created_at=story.created_at.isoformat(),
                permalink=f"/s/{story.short_id}",
                audio_url=f"/s/{story.short_id}/audio",
            )
            for story in stories
        ]
        
        has_more = (offset + len(stories)) < total
        
        return StoriesListResponse(
            stories=story_responses,
            total=total,
            has_more=has_more
        )
    finally:
        db.close()
