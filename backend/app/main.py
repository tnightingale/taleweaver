import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.config import router as config_router
from app.routes.story import router as story_router

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
