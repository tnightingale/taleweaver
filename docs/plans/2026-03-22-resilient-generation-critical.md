# Resilient Story Generation - Critical Improvements

**Feature:** Error Handling, Quota Management, and Partial Result Recovery  
**Created:** 2026-03-22  
**Priority:** 🔴 CRITICAL  
**Estimated Time:** 8-12 hours

---

## Problem Statement

### Current Critical Issues

**1. Complete Data Loss on Failures**
- Voice synthesis fails at segment 7 of 12 → segments 1-6 completely lost
- Must regenerate entire story from scratch (waste expensive LLM + TTS quota)
- No way to resume or recover partial work

**2. Only First Illustration Generates** (Active Bug in Production)
- Illustration loop stops after 1 image with no error logs
- Likely Google API quota/rate limit hit silently
- 7 images worth of quota wasted (metadata not preserved)
- Story shows `has_illustrations: true` but only 1 image displays

**3. No Quota/Rate Limit Handling**
- Services fail fast with no retry logic
- No distinction between retryable vs. permanent errors
- No graceful degradation when quota exhausted
- Silent failures (no logs, no user feedback)

**4. Poor Error Visibility**
- Generic error messages ("Something went wrong")
- No indication of progress made before failure
- No actionable recovery options for users
- Debugging requires diving into container logs

---

## Research Findings

### Error Handling Audit Results

| Node | Error Handling | Partial Results | Recovery | Grade |
|------|----------------|-----------------|----------|-------|
| story_writer | ❌ None | ❌ Lost | ❌ No | F |
| scene_analyzer | ✅ Graceful | ✅ Skips illustrations | ✅ Yes | A |
| script_splitter | ❌ None | ❌ Lost | ❌ No | F |
| voice_synthesizer | ❌ None | ❌ Lost | ❌ No | **F (CRITICAL)** |
| illustration_generator | ⚠️ Partial | ❌ Orphaned | ❌ No | **D (CRITICAL)** |
| audio_stitcher | ❌ None | ❌ Lost | ❌ No | F |

**Overall Grade:** ❌ **F - Fail-fast with no recovery**

**Only scene_analyzer has proper error handling!**

---

## Scope: Focus on Critical Path

Given the active production bug and highest-value improvements:

### Phase 1: Fix Illustration Generator (IMMEDIATE - 2-3 hours)
**Impact:** Fixes current bug, preserves partial images  
**Complexity:** Low  
**Priority:** 🔴 CRITICAL

### Phase 2: Voice Synthesizer Resilience (HIGH - 3-4 hours)
**Impact:** Prevents worst data loss (expensive TTS quota)  
**Complexity:** Medium  
**Priority:** 🔴 HIGH

### Phase 3: Enhanced Error UX (MEDIUM - 2-3 hours)
**Impact:** Better user communication and recovery options  
**Complexity:** Medium  
**Priority:** 🟡 MEDIUM

---

## Phase 1: Fix Illustration Generator Bug (IMMEDIATE)

### Estimated Time: 2-3 hours

### Root Cause Analysis

**From production logs (story aa0a8b72...):**
```
18:27:26 - ✅ Illustration 1/8 generated (scene_0.png saved)
18:27:42 - 🛑 Loop stops (no logs for images 2-8)
18:27:42 - ❌ No error logs visible
18:28:02 - Story completes with only 1 image
```

**Why the loop stopped:**
1. Image 2 generation attempted with `reference_image_url` set
2. Provider code: "Reference image support not yet implemented" (line 80)
3. Google API call likely failed (quota/rate limit/error) 
4. Exception caught by outer try/except (line 104)
5. Returns `{"scenes": scenes}` WITHOUT preserving partial work
6. Since only scene[0] was updated before exception, only 1 image in result

**Current Code Problem:**
```python
# Lines 61-99: Main loop
for i, scene in enumerate(scenes):
    # ... generate image ...
    scene["image_path"] = image_path  # Mutates scene in-place
    scene["image_url"] = image_url

# Line 104: Exception handler
except Exception as e:
    logger.error(f"Illustration generation failed: {e}")
    return {"scenes": scenes, "error": "..."}  
    # ⬆️ Returns scenes, but only scene[0] was updated before exception!
```

### Solution: Per-Image Error Handling

#### Task 1.1: Granular Exception Handling

**File:** `backend/app/graph/nodes/illustration_generator.py`

```python
async def illustration_generator(state: StoryState) -> dict:
    # ... setup code (lines 1-60) ...
    
    successful_count = 0
    failed_count = 0
    errors = []  # Track all errors
    
    for i, scene in enumerate(scenes):
        try:
            logger.info(f"🎨 Generating illustration {i+1}/{len(scenes)}: {scene['beat_name']}")
            
            # Build full prompt
            char_desc = state.get("character_description", "")
            if i == 0 and char_desc:
                full_prompt = f"{char_desc}. {scene['illustration_prompt']}"
            else:
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
            
            # Update THIS scene's metadata immediately
            scene["image_path"] = image_path
            scene["image_url"] = image_url
            scene["generation_metadata"] = {
                "provider": provider.get_provider_info()["name"],
                "model": provider.get_provider_info()["model"],
                "art_style": art_style_id,
                "reference_image": previous_image_url,
                "index": i,
                "succeeded": True,
            }
            
            successful_count += 1
            previous_image_url = image_url
            
            logger.info(f"✅ Illustration {i+1}/{len(scenes)} completed: {image_path}")
            
        except Exception as e:
            # Log detailed error for THIS specific image
            logger.exception(f"❌ Failed to generate illustration {i+1}/{len(scenes)} (beat: {scene['beat_name']})")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error message: {str(e)}")
            logger.error(f"   Prompt length: {len(full_prompt)} chars")
            if previous_image_url:
                logger.error(f"   Reference image: {previous_image_url}")
            
            # Record failure in scene metadata
            scene["image_path"] = None
            scene["image_url"] = None
            scene["generation_metadata"] = {
                "provider": provider.get_provider_info()["name"],
                "index": i,
                "succeeded": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }
            
            failed_count += 1
            errors.append({
                "index": i,
                "beat": scene['beat_name'],
                "error": str(e)
            })
            
            # IMPORTANT: Continue to next image (don't break)
            # Some failures are transient - next image might succeed
            continue
    
    # Build response based on results
    total = len(scenes)
    
    if successful_count == 0:
        logger.error(f"❌ Illustration generation: 0/{total} succeeded - complete failure")
        return {
            "scenes": scenes,  # All have null image_url
            "error": f"Illustration generation failed: {errors[0]['error'] if errors else 'Unknown error'}"
        }
    
    elif successful_count < total:
        logger.warning(f"⚠️ Illustration generation: {successful_count}/{total} succeeded - partial success")
        return {
            "scenes": scenes,  # Has partial image_url data
            "partial_illustrations": True,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "errors": errors,
            "error": f"Generated {successful_count} of {total} illustrations. {failed_count} failed."
        }
    
    else:
        logger.info(f"✅ Illustration generation: {total}/{total} succeeded - complete success")
        return {"scenes": scenes}
```

**Key Improvements:**
- ✅ Try/except **per image** (not whole loop)
- ✅ `continue` on error (don't stop loop)
- ✅ `logger.exception()` captures full traceback
- ✅ Log error type, message, context
- ✅ Track successful vs. failed count
- ✅ Return partial results with detailed error info
- ✅ Mark each scene's generation_metadata with success/failure

#### Task 1.2: Better Provider Logging

**File:** `backend/app/services/illustration/nanobanana.py`

```python
async def generate_image(self, prompt, art_style, reference_image_url=None, **kwargs):
    full_prompt = f"{prompt}, {art_style}" if art_style else prompt
    
    logger.info(f"🎨 Google Gemini API call starting...")
    logger.debug(f"   Prompt: {full_prompt[:200]}...")
    logger.debug(f"   Reference image: {reference_image_url}")
    
    try:
        # ... existing code ...
        
        logger.info(f"✅ Image generated: {len(png_bytes)} bytes")
        return png_bytes
        
    except Exception as e:
        # Enhanced error logging
        logger.exception(f"❌ Google Gemini API error")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Error message: {str(e)}")
        logger.error(f"   Prompt length: {len(full_prompt)} chars")
        logger.error(f"   Model: {self.model_id}")
        
        # Check for specific error types
        if "quota" in str(e).lower():
            logger.error(f"   🔴 QUOTA ERROR - Google Gemini quota exceeded")
        elif "429" in str(e) or "rate limit" in str(e).lower():
            logger.error(f"   🔴 RATE LIMIT - Too many requests to Google API")
        
        raise  # Re-raise with context
```

#### Task 1.3: Add Error Classification

**File:** `backend/app/graph/nodes/illustration_generator.py`

```python
def _classify_image_error(e: Exception) -> dict:
    """Classify error type for better handling"""
    msg = str(e).lower()
    error_type = type(e).__name__
    
    return {
        "is_quota": any(k in msg for k in ['quota', 'limit exceeded', 'insufficient credits']),
        "is_rate_limit": any(k in msg for k in ['429', 'rate limit', 'too many requests']),
        "is_network": any(k in msg for k in ['timeout', 'connection', 'network', '503', '502']),
        "is_auth": any(k in msg for k in ['auth', 'api key', '401', '403']),
        "is_permanent": 'content policy' in msg or 'invalid request' in msg,
        "error_type": error_type,
        "message": str(e),
    }

# In loop exception handler:
except Exception as e:
    error_info = _classify_image_error(e)
    
    logger.exception(f"❌ Failed illustration {i+1}")
    logger.error(f"   Classification: {error_info}")
    
    if error_info["is_quota"]:
        logger.error(f"   🔴 QUOTA EXCEEDED - Stop generating more images")
        # Don't continue loop if quota issue (would fail anyway)
        break
    elif error_info["is_rate_limit"]:
        logger.warning(f"   ⏸️ RATE LIMITED - Wait and try next image")
        await asyncio.sleep(2)  # Brief pause before next attempt
    
    # Record in metadata
    scene["generation_metadata"] = {
        "succeeded": False,
        "error_classification": error_info
    }
    
    continue  # Try next image unless quota exceeded
```

#### Task 1.4: Update Database Schema

**Add to JobState model:**
```python
partial_illustrations_count = Column(Integer)  # How many images generated
partial_audio_segments = Column(Integer)  # How many segments synthesized
```

**Update mark_job_complete:**
```python
def mark_job_complete(db, job_id, ..., partial_illustrations_count=None):
    job.partial_illustrations_count = partial_illustrations_count or 0
    # ...
```

#### Task 1.5: Tests (TDD)

**File:** `backend/tests/test_illustration_generator_resilience.py`

```python
@pytest.mark.asyncio
async def test_illustration_generator_continues_on_single_failure():
    """Should continue generating images after one fails"""
    # Mock provider to fail on image 3, succeed on others
    # Verify scenes 0,1,2,4,5,6,7 have image_url
    # Verify scene 3 has null image_url
    # Verify partial_illustrations flag
    # Verify error list has 1 entry

@pytest.mark.asyncio  
async def test_illustration_generator_stops_on_quota_error():
    """Should stop immediately on quota errors"""
    # Mock provider to raise quota error on image 2
    # Verify scene 0,1 have image_url
    # Verify scenes 2-7 have null image_url
    # Verify error indicates quota exceeded

@pytest.mark.asyncio
async def test_illustration_generator_logs_detailed_errors():
    """Should log error type, message, and context"""
    # Mock provider to fail with various error types
    # Verify logs contain error classification
    # Verify logs contain prompt and reference image info
```

---

## Phase 2: Voice Synthesizer Resilience (HIGH)

### Estimated Time: 3-4 hours

### Solution: Incremental Saves + Retry + Resume

#### Task 2.1: Save Segments Incrementally

**File:** `backend/app/graph/nodes/voice_synthesizer.py`

```python
async def voice_synthesizer(state: StoryState) -> dict:
    from app.db.crud import get_job_state, update_job_progress
    from app.utils.storage import save_temp_audio_segment, load_temp_audio_segments
    
    job_id = state.get("job_id")
    segments = state["segments"]
    
    # Try to resume from checkpoint (if job was retried)
    existing_segments = []
    if job_id:
        existing_segments = load_temp_audio_segments(job_id)
        if existing_segments:
            logger.info(f"📥 Loaded {len(existing_segments)} previously synthesized segments")
    
    start_index = len(existing_segments)
    audio_segments = existing_segments.copy()
    
    client = _get_client()
    
    for i in range(start_index, len(segments)):
        segment = segments[i]
        voice_id = _get_voice_id(segment["voice_type"])
        
        try:
            # Synthesize with retry logic
            audio_bytes = await _synthesize_with_retry(
                client, voice_id, segment["text"],
                max_retries=3
            )
            
            audio_segments.append(audio_bytes)
            
            # SAVE IMMEDIATELY to temp storage
            if job_id:
                save_temp_audio_segment(job_id, i, audio_bytes)
                
                # Update progress in database
                db = SessionLocal()
                try:
                    update_job_progress(
                        db, job_id, 
                        progress=(i+1)/len(segments) * 100,
                        detail=f"Synthesized segment {i+1} of {len(segments)}"
                    )
                finally:
                    db.close()
            
            logger.info(f"✅ Synthesized segment {i+1}/{len(segments)}: {segment['speaker']}")
            
        except QuotaExceededError as e:
            # Quota errors are NOT retryable immediately
            logger.error(f"🔴 ElevenLabs quota exceeded at segment {i+1}/{len(segments)}")
            
            # Mark job as quota_exceeded (resumable)
            if job_id:
                db = SessionLocal()
                try:
                    job = get_job_state(db, job_id)
                    job.resumable = True
                    job.partial_data_json = json.dumps({
                        "segments_completed": i,
                        "segments_total": len(segments),
                        "checkpoint_node": "voice_synthesizer"
                    })
                    db.commit()
                finally:
                    db.close()
            
            return {
                "audio_segments": audio_segments,
                "partial_completion": i,
                "resumable": True,
                "error": f"Voice synthesis quota exceeded after {i} of {len(segments)} segments"
            }
        
        except RateLimitError as e:
            # Rate limits might clear quickly - log and continue after backoff
            logger.warning(f"⏸️ Rate limit at segment {i+1}, retries exhausted")
            # Return partial results (could resume later)
            return {
                "audio_segments": audio_segments,
                "partial_completion": i,
                "resumable": True,
                "error": f"Rate limit exceeded after {i} segments"
            }
        
        except Exception as e:
            # Permanent errors
            logger.exception(f"❌ Failed at segment {i+1}/{len(segments)}")
            return {
                "audio_segments": audio_segments,
                "partial_completion": i,
                "resumable": False,
                "error": str(e)
            }
    
    # Cleanup temp files on success
    if job_id:
        cleanup_temp_audio(job_id)
    
    return {"audio_segments": audio_segments}
```

#### Task 2.2: Custom Exception Classes

**File:** `backend/app/graph/nodes/voice_synthesizer.py`

```python
class QuotaExceededError(Exception):
    """Raised when API quota is exceeded (not retryable immediately)"""
    pass

class RateLimitError(Exception):
    """Raised when API rate limit hit (retryable with backoff)"""
    pass

def _classify_elevenlabs_error(e: Exception):
    """Classify ElevenLabs API errors"""
    msg = str(e).lower()
    
    if "quota" in msg or "limit exceeded" in msg:
        raise QuotaExceededError(str(e))
    elif "429" in msg or "rate limit" in msg:
        raise RateLimitError(str(e))
    else:
        raise e  # Unknown error, re-raise as-is
```

#### Task 2.3: Retry with Exponential Backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class TransientError(Exception):
    """Errors that should be retried"""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(TransientError),
    before_sleep=lambda retry_state: logger.warning(f"⏳ Retry in {retry_state.next_action.sleep:.0f}s (attempt {retry_state.attempt_number}/3)...")
)
async def _synthesize_with_retry(client, voice_id, text, max_retries=3):
    """Synthesize audio with retry logic for transient errors"""
    try:
        return await asyncio.to_thread(
            _synthesize_segment, client, voice_id, text
        )
    except Exception as e:
        msg = str(e).lower()
        
        # Classify error
        if "quota" in msg or "limit exceeded" in msg:
            raise QuotaExceededError(str(e))  # Don't retry
        elif "429" in msg or "rate limit" in msg:
            raise RateLimitError(str(e))  # Don't retry (handled at higher level)
        elif any(k in msg for k in ['timeout', '503', '502', 'network', 'connection']):
            raise TransientError(str(e))  # Retry
        else:
            raise  # Unknown error, don't retry
```

#### Task 2.4: Temp Audio Storage

**File:** `backend/app/utils/storage.py`

```python
def save_temp_audio_segment(job_id: str, index: int, audio_bytes: bytes) -> str:
    """
    Save audio segment to temp storage for resume capability.
    
    Args:
        job_id: Job UUID
        index: Segment index
        audio_bytes: MP3 audio data
        
    Returns:
        Path where segment was saved
    """
    temp_dir = settings.storage_path / "temp" / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    segment_path = temp_dir / f"segment_{index}.mp3"
    segment_path.write_bytes(audio_bytes)
    
    logger.debug(f"Saved temp audio segment: {segment_path} ({len(audio_bytes)} bytes)")
    return str(segment_path)


def load_temp_audio_segments(job_id: str) -> List[bytes]:
    """
    Load previously saved audio segments (for resume).
    
    Returns:
        List of audio bytes in order
    """
    temp_dir = settings.storage_path / "temp" / job_id
    if not temp_dir.exists():
        return []
    
    segments = []
    for i in range(100):  # Max reasonable segment count
        segment_path = temp_dir / f"segment_{i}.mp3"
        if not segment_path.exists():
            break
        segments.append(segment_path.read_bytes())
    
    return segments


def cleanup_temp_audio(job_id: str):
    """Remove temp audio files after job completes or permanently fails"""
    temp_dir = settings.storage_path / "temp" / job_id
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        logger.info(f"🗑️ Cleaned up temp audio for job {job_id}")
```

#### Task 2.5: Tests

```python
@pytest.mark.asyncio
async def test_voice_synthesizer_saves_segments_incrementally(test_db):
    """Should save each segment as it's synthesized"""
    # Mock to succeed on all segments
    # Verify temp files created for each
    # Verify all segments returned

@pytest.mark.asyncio
async def test_voice_synthesizer_quota_error_preserves_partial(test_db):
    """Should preserve partial segments on quota error"""
    # Mock to fail with quota error at segment 5
    # Verify segments 0-4 saved to temp storage
    # Verify resumable flag set
    # Verify partial_completion = 4

@pytest.mark.asyncio
async def test_voice_synthesizer_resumes_from_checkpoint(test_db):
    """Should resume from previously saved segments"""
    # Create temp segments 0-4
    # Run voice_synthesizer
    # Verify it starts from segment 5
    # Verify final output has all 12 segments
```

---

## Phase 3: Enhanced Error UX (MEDIUM)

### Estimated Time: 2-3 hours

### Task 3.1: Structured Error Responses

**Update JobStatusResponse:**
```python
class PartialProgress(BaseModel):
    segments_completed: Optional[int]
    segments_total: Optional[int]
    illustrations_completed: Optional[int]
    illustrations_total: Optional[int]
    checkpoint_node: Optional[str]

class JobStatusResponse(BaseModel):
    # ... existing fields ...
    resumable: bool = False
    partial_progress: Optional[PartialProgress] = None
    error_details: Optional[str] = None  # Technical error for debugging
```

### Task 3.2: Frontend Error Display

**File:** `frontend/src/components/StoryScreen.tsx`

```tsx
// Enhanced error state display
{status === "failed" && storyData && (
  <motion.div className="glass-card p-6 space-y-4 max-w-md">
    <h2 className="text-xl font-display text-red-400">
      Generation Failed
    </h2>
    
    <p className="text-starlight/80">
      {storyData.error || "Something went wrong"}
    </p>
    
    {/* Show partial progress if available */}
    {storyData.partial_progress && (
      <div className="space-y-2 text-sm text-starlight/60">
        <p className="font-semibold">Progress before failure:</p>
        <ul className="list-disc list-inside">
          {storyData.partial_progress.segments_completed && (
            <li>
              ✅ Voice: {storyData.partial_progress.segments_completed} of{" "}
              {storyData.partial_progress.segments_total} segments
            </li>
          )}
          {storyData.partial_progress.illustrations_completed && (
            <li>
              ✅ Images: {storyData.partial_progress.illustrations_completed} of{" "}
              {storyData.partial_progress.illustrations_total} illustrations
            </li>
          )}
        </ul>
      </div>
    )}
    
    {/* Retry button if resumable */}
    {storyData.resumable && (
      <button
        onClick={() => handleRetry(jobId)}
        className="btn-glow text-sm w-full"
      >
        🔄 Try Again (Resume from {storyData.partial_progress?.checkpoint_node})
      </button>
    )}
    
    {/* Start over button */}
    <button
      onClick={onCreateAnother}
      className="px-6 py-3 rounded-xl glass-card text-ethereal hover:text-white text-sm"
    >
      ✨ Start Over
    </button>
  </motion.div>
)}
```

### Task 3.3: Retry Endpoint

**File:** `backend/app/routes/story.py`

```python
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
            raise HTTPException(404, "Job not found")
        
        if job.status not in ["failed", "partial"]:
            raise HTTPException(400, "Job is not in a failed state")
        
        if not job.resumable:
            raise HTTPException(400, "Job cannot be resumed (permanent error)")
        
        if job.retry_count >= 3:
            raise HTTPException(400, "Maximum retry limit reached (3 attempts)")
        
        # Load checkpoint
        checkpoint = json.loads(job.partial_data_json) if job.partial_data_json else {}
        
        # Update retry count
        job.retry_count += 1
        job.status = "processing"
        job.error_message = None
        db.commit()
        
        # Resume pipeline (with checkpoint state)
        # TODO: Implement resume logic in run_pipeline
        asyncio.create_task(run_pipeline(job_id, checkpoint.get("state", {})))
        
        return {"job_id": job_id, "status": "resuming", "retry_count": job.retry_count}
        
    finally:
        db.close()
```

---

## Implementation Plan

### Step 1: Immediate Fix (Illustration Bug)

**Timeline:** Today (2-3 hours)

1. [ ] Update illustration_generator.py with per-image try/except
2. [ ] Add error classification helper
3. [ ] Improve provider logging (nanobanana.py)
4. [ ] Write 3 tests for partial failures
5. [ ] Test in Docker
6. [ ] Deploy fix to production
7. [ ] Verify next story generates multiple images

**Deliverable:** Stories generate partial illustrations instead of failing completely

---

### Step 2: Voice Synthesizer Resilience

**Timeline:** Next session (3-4 hours)

1. [ ] Add temp audio storage functions
2. [ ] Update voice_synthesizer with incremental saves
3. [ ] Add retry logic with tenacity
4. [ ] Add custom exception classes
5. [ ] Update JobState model (resumable, partial_data_json)
6. [ ] Add migration for new columns
7. [ ] Write 5 tests
8. [ ] Test resume functionality

**Deliverable:** Voice synthesis preserves partial work on quota errors

---

### Step 3: Error UX

**Timeline:** Future (2-3 hours)

1. [ ] Update API response models
2. [ ] Add retry endpoint
3. [ ] Update frontend error display
4. [ ] Add "Try Again" button
5. [ ] Test E2E retry flow

**Deliverable:** Users can resume failed jobs, see partial progress

---

## Testing Strategy

### Unit Tests
```python
# Test each error scenario
- test_illustration_single_failure_continues
- test_illustration_quota_stops_immediately
- test_voice_quota_saves_partial
- test_voice_rate_limit_retries
- test_voice_resume_from_checkpoint
```

### Integration Tests
```python
# Test full pipeline with injected failures
- test_pipeline_illustration_partial_success
- test_pipeline_voice_quota_recovery
- test_retry_endpoint_resumes_job
```

### Manual Testing
1. [ ] Generate story, kill Google API key mid-generation
2. [ ] Verify partial images saved
3. [ ] Check logs for detailed errors
4. [ ] Try resume flow

---

## Success Criteria

### Phase 1 (Immediate)
- [ ] Stories generate 2+ illustrations (partial success)
- [ ] Logs show detailed error for failed images
- [ ] Database preserves partial illustration metadata
- [ ] No silent failures

### Phase 2 (Voice)
- [ ] Quota errors preserve completed segments
- [ ] Rate limits trigger automatic retry
- [ ] Users can resume from checkpoint
- [ ] No complete data loss

### Phase 3 (UX)
- [ ] Users see "7 of 12 segments completed" in errors
- [ ] "Try Again" button for resumable failures
- [ ] Clear distinction between quota vs. rate limit vs. permanent errors

---

## Dependencies

**Add to requirements.txt:**
```
tenacity==9.0.0  # Retry logic with exponential backoff
```

---

## Risks & Mitigations

**Risk 1: Temp storage fills disk**
- Mitigation: Cleanup after 24 hours
- Mitigation: Max 10MB per job (reasonable for audio segments)

**Risk 2: Resume creates inconsistencies**
- Mitigation: Thorough testing of checkpoint/resume
- Mitigation: Validate state before resuming

**Risk 3: Retries waste quota**
- Mitigation: Only retry transient errors (not quota)
- Mitigation: Max 3 retry attempts per segment

---

## Files Summary

### Phase 1 (Immediate)
- `backend/app/graph/nodes/illustration_generator.py` - Per-image errors
- `backend/app/services/illustration/nanobanana.py` - Better logging
- `backend/tests/test_illustration_generator_resilience.py` - NEW (3 tests)

### Phase 2 (High)
- `backend/app/graph/nodes/voice_synthesizer.py` - Incremental saves + retry
- `backend/app/utils/storage.py` - Temp audio storage
- `backend/app/db/models.py` - Add resumable fields
- `backend/app/db/migrate.py` - Add migrations
- `backend/app/db/crud.py` - Update job state helpers
- `backend/tests/test_voice_synthesizer_resilience.py` - NEW (5 tests)
- `requirements.txt` - Add tenacity

### Phase 3 (Medium)
- `backend/app/routes/story.py` - Retry endpoint
- `backend/app/models/responses.py` - Enhanced error types
- `frontend/src/components/StoryScreen.tsx` - Error UI
- `frontend/src/api/client.ts` - Retry API call
- `frontend/src/types/index.ts` - Error types

---

## Estimated Timeline

| Phase | Time | Complexity | Priority |
|-------|------|------------|----------|
| 1. Fix illustration bug | 2-3h | Low | 🔴 CRITICAL |
| 2. Voice resilience | 3-4h | Medium | 🔴 HIGH |
| 3. Error UX | 2-3h | Medium | 🟡 MEDIUM |
| **Total** | **7-10h** | | |

---

**Recommendation:** Start with Phase 1 immediately to fix the active production bug.

**This plan addresses the most critical issue (only 1 illustration) and lays foundation for quota/recovery management.**
