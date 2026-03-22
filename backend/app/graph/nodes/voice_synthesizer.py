import asyncio
import logging
import time

from elevenlabs import ElevenLabs
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.graph.state import StoryState
from app.utils.storage import save_temp_audio_segment, load_temp_audio_segments, cleanup_temp_audio

logger = logging.getLogger(__name__)


# Custom exception classes for error handling
class QuotaExceededError(Exception):
    """Raised when API quota is exceeded (not retryable immediately)"""
    pass


class RateLimitError(Exception):
    """Raised when API rate limit is hit (retryable with backoff)"""
    pass


class TransientError(Exception):
    """Errors that should be retried (network timeouts, 503, etc.)"""
    pass


def _get_voice_id(voice_type: str) -> str:
    mapping = {
        "narrator": settings.narrator_voice_id,
        "male": settings.character_male_voice_id,
        "female": settings.character_female_voice_id,
        "child": settings.character_child_voice_id,
    }
    return mapping.get(voice_type, settings.narrator_voice_id)


def _classify_error(e: Exception):
    """
    Classify ElevenLabs API errors into categories.
    
    Raises appropriate exception type for handling.
    """
    msg = str(e).lower()
    
    # Quota errors (not retryable immediately)
    if any(keyword in msg for keyword in ['quota', 'limit exceeded', 'insufficient credits', 'usage limit']):
        raise QuotaExceededError(str(e))
    
    # Rate limit errors (retryable with backoff)
    elif any(keyword in msg for keyword in ['429', 'rate limit', 'too many requests', 'slow down']):
        raise RateLimitError(str(e))
    
    # Transient errors (retryable)
    elif any(keyword in msg for keyword in ['timeout', '503', '502', 'network', 'connection', 'temporary']):
        raise TransientError(str(e))
    
    # Unknown error - re-raise as-is
    else:
        raise e


def _synthesize_segment(client: ElevenLabs, voice_id: str, text: str) -> bytes:
    """Synthesize single segment with error classification"""
    try:
        audio_iter = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
        )
        return b"".join(audio_iter)
    except Exception as e:
        _classify_error(e)  # Raises QuotaExceededError, RateLimitError, TransientError, or original
        raise  # Should never reach here (classify always raises)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(TransientError),
    before_sleep=lambda retry_state: logger.warning(
        f"⏳ Retrying TTS in {retry_state.next_action.sleep:.0f}s (attempt {retry_state.attempt_number}/3)..."
    )
)
async def _synthesize_with_retry(client: ElevenLabs, voice_id: str, text: str) -> bytes:
    """
    Synthesize audio with automatic retry for transient errors.
    
    Retries up to 3 times with exponential backoff for:
    - Network timeouts
    - 503 Service Unavailable
    - Connection errors
    
    Does NOT retry:
    - Quota exceeded (QuotaExceededError)
    - Rate limits (RateLimitError) - handled at higher level
    """
    return await asyncio.to_thread(_synthesize_segment, client, voice_id, text)


async def voice_synthesizer(state: StoryState) -> dict:
    """
    Synthesize voice audio for all segments.
    
    Features:
    - Saves each segment incrementally (for resume capability)
    - Retries transient errors automatically
    - Preserves partial results on quota/rate limit errors
    - Updates job progress in database
    
    Returns:
        dict with audio_segments, or partial results on error
    """
    from app.db.crud import get_job_state, update_job_progress
    from app.db.database import SessionLocal
    
    client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    job_id = state.get("job_id")
    segments = state["segments"]
    
    # Try to resume from checkpoint (if job was retried after failure)
    existing_segments = []
    if job_id:
        existing_segments = load_temp_audio_segments(job_id)
        if existing_segments:
            logger.info(f"📥 Loaded {len(existing_segments)} previously synthesized segments")
    
    start_index = len(existing_segments)
    audio_segments = existing_segments.copy()
    
    total_start = time.time()
    
    for i in range(start_index, len(segments)):
        segment = segments[i]
        voice_id = _get_voice_id(segment["voice_type"])
        
        try:
            seg_start = time.time()
            
            # Synthesize with automatic retry for transient errors
            audio_bytes = await _synthesize_with_retry(client, voice_id, segment["text"])
            
            audio_segments.append(audio_bytes)
            elapsed = time.time() - seg_start
            
            # Save segment immediately to temp storage
            if job_id:
                save_temp_audio_segment(job_id, i, audio_bytes)
                
                # Update job progress in database (optional - may not exist in tests)
                try:
                    db = SessionLocal()
                    try:
                        progress_pct = ((i + 1) / len(segments)) * 100
                        update_job_progress(
                            db, job_id,
                            progress=progress_pct,
                            detail=f"Synthesized segment {i+1} of {len(segments)}"
                        )
                    finally:
                        db.close()
                except Exception as db_err:
                    # Database errors shouldn't stop synthesis
                    logger.debug(f"Could not update job progress: {db_err}")
            
            logger.info(f"✅ TTS segment {i+1}/{len(segments)}: voice={segment['voice_type']}, chars={len(segment['text'])}, bytes={len(audio_bytes)}, time={elapsed:.1f}s")
            
        except QuotaExceededError as e:
            # Quota errors are NOT retryable - save state and return partial results
            logger.error(f"🔴 ElevenLabs quota exceeded at segment {i+1}/{len(segments)}")
            logger.error(f"   Partial segments saved: {i} of {len(segments)}")
            logger.error(f"   Error: {str(e)}")
            
            # Mark job as resumable in database (optional)
            if job_id:
                try:
                    db = SessionLocal()
                    try:
                        job = get_job_state(db, job_id)
                        if job:
                            import json
                            job.resumable = True
                            job.partial_data_json = json.dumps({
                                "segments_completed": i,
                                "segments_total": len(segments),
                                "checkpoint_node": "voice_synthesizer"
                            })
                            db.commit()
                    finally:
                        db.close()
                except Exception as db_err:
                    logger.debug(f"Could not mark job as resumable: {db_err}")
            
            return {
                "audio_segments": audio_segments,
                "partial_completion": i,
                "resumable": True,
                "error": f"Voice synthesis quota exceeded after {i} of {len(segments)} segments"
            }
        
        except RateLimitError as e:
            # Rate limit hit - return partial results (user can retry)
            logger.warning(f"⏸️ ElevenLabs rate limit at segment {i+1}/{len(segments)}")
            logger.warning(f"   Partial segments saved: {i} of {len(segments)}")
            
            if job_id:
                try:
                    db = SessionLocal()
                    try:
                        job = get_job_state(db, job_id)
                        if job:
                            import json
                            job.resumable = True
                            job.partial_data_json = json.dumps({
                                "segments_completed": i,
                                "segments_total": len(segments),
                                "checkpoint_node": "voice_synthesizer"
                            })
                            db.commit()
                    finally:
                        db.close()
                except Exception as db_err:
                    logger.debug(f"Could not mark job as resumable: {db_err}")
            
            return {
                "audio_segments": audio_segments,
                "partial_completion": i,
                "resumable": True,
                "error": f"Rate limit reached after {i} segments. Please wait and try again."
            }
        
        except Exception as e:
            # Unexpected error (permanent)
            logger.exception(f"❌ Failed to synthesize segment {i+1}/{len(segments)}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Partial segments saved: {i} of {len(segments)}")
            
            return {
                "audio_segments": audio_segments,
                "partial_completion": i,
                "resumable": False,  # Unknown error - not safe to resume
                "error": str(e)
            }
    
    # All segments synthesized successfully
    total_elapsed = time.time() - total_start
    logger.info(f"✅ TTS complete: {len(audio_segments)} segments in {total_elapsed:.1f}s")
    
    # Cleanup temp files on success
    if job_id:
        cleanup_temp_audio(job_id)
    
    return {"audio_segments": audio_segments}
