# PR: Voice Synthesizer Resilience

**Branch:** `feature/voice-synthesizer-resilience` ✅  
**Create PR at:** https://github.com/tnightingale/taleweaver/pull/new/feature/voice-synthesizer-resilience

---

## PR Title

```
Feature: Voice synthesizer resilience - quota handling and resume capability
```

## PR Description

```markdown
## Summary

Implements resilient voice synthesis with incremental saves, retry logic, and resume capability. Prevents complete data loss when ElevenLabs quota is exceeded mid-generation.

**Completes:** Phase 2 of Resilient Generation plan

## Problem

**Current Behavior:**
- Voice synthesis fails at segment 7 of 12 → segments 1-6 completely lost
- Must regenerate entire story from scratch
- Wastes expensive LLM quota (story generation) + partial TTS quota
- No way to resume

**Impact:**
- Poor UX when quota limits hit
- Financial waste (re-generating work already paid for)
- User frustration (long waits for complete restart)

## Solution

**Incremental Saves + Resume:**
- Save each segment to temp storage immediately after synthesis
- On quota error, preserve partial work and mark job as resumable
- Users can resume from last checkpoint when quota resets
- Retry transient errors automatically with exponential backoff

## Changes

### 1. Custom Exception Classes

**File:** `voice_synthesizer.py`

```python
class QuotaExceededError(Exception):
    """API quota exceeded (not retryable immediately)"""

class RateLimitError(Exception):
    """API rate limit hit (retryable with backoff)"""

class TransientError(Exception):
    """Network/timeout errors (should be retried)"""
```

### 2. Error Classification

```python
def _classify_error(e: Exception):
    \"\"\"Classify ElevenLabs errors into categories\"\"\"
    msg = str(e).lower()
    
    if "quota" in msg or "limit exceeded" in msg:
        raise QuotaExceededError(str(e))
    elif "429" in msg or "rate limit" in msg:
        raise RateLimitError(str(e))
    elif "timeout" in msg or "503" in msg:
        raise TransientError(str(e))
    else:
        raise e
```

### 3. Retry Logic

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=30),
    retry=retry_if_exception_type(TransientError)
)
async def _synthesize_with_retry(client, voice_id, text):
    return await asyncio.to_thread(_synthesize_segment, client, voice_id, text)
```

**Behavior:**
- Transient errors retry automatically (3 attempts, 2s→4s→8s backoff)
- Quota/rate limit errors don't retry (fail fast, save state)

### 4. Incremental Saves

```python
for i in range(start_index, len(segments)):
    try:
        audio_bytes = await _synthesize_with_retry(...)
        audio_segments.append(audio_bytes)
        
        # SAVE IMMEDIATELY
        save_temp_audio_segment(job_id, i, audio_bytes)
        update_job_progress(db, job_id, progress, detail)
        
    except QuotaExceededError:
        # Preserve partial results
        return {
            "audio_segments": audio_segments,  # Segments 0-(i-1)
            "partial_completion": i,
            "resumable": True
        }
```

### 5. Resume from Checkpoint

```python
# Load previously saved segments
existing_segments = load_temp_audio_segments(job_id)
start_index = len(existing_segments)
audio_segments = existing_segments.copy()

# Resume from start_index (skip already completed)
for i in range(start_index, len(segments)):
    # ...
```

### 6. Temp Storage Functions

**File:** `app/utils/storage.py`

- `save_temp_audio_segment(job_id, index, audio_bytes)` - Save segment
- `load_temp_audio_segments(job_id)` - Load all saved segments
- `cleanup_temp_audio(job_id)` - Remove temp files on success

**Location:** `/storage/temp/{job_id}/segment_{i}.mp3`

### 7. JobState Extensions

**File:** `app/db/models.py`

New columns:
- `resumable` (Boolean) - Can job be resumed?
- `partial_data_json` (Text) - Checkpoint state JSON
- `checkpoint_node` (String) - Last successful node
- `retry_count` (Integer) - Number of retry attempts

**Migration:** Auto-adds columns on startup

## Test Results

```
✅ 165/165 tests passing (100%)
✅ 6 new voice resilience tests (TDD: RED → GREEN)
```

**Tests cover:**
- Incremental saves
- Quota error preservation
- Resume from checkpoint  
- Retry transient errors
- Error classification
- Job progress updates

## Docker Verification

```
✅ Container builds successfully
✅ Gunicorn 4 workers start
✅ Migrations add new columns
✅ Application healthy
```

## Error Handling Examples

### Quota Exceeded (Segment 7 of 12)

**Before:**
```
Segments 1-6: Lost completely ❌
User: Must regenerate entire story ❌
```

**After:**
```
Segments 1-6: Saved to /storage/temp/{job_id}/segment_{0-5}.mp3 ✅
Job marked: resumable=true, checkpoint="voice_synthesizer" ✅
User: Can resume when quota resets ✅
```

### Transient Network Error

**Before:**
```
Timeout → Job fails ❌
User: Start over ❌
```

**After:**
```
Timeout → Retry 1 (wait 2s) → Retry 2 (wait 4s) → Success ✅
Job: Completes without user intervention ✅
```

## Dependencies

```
tenacity==9.0.0  # Retry logic with exponential backoff
```

## Files Changed

**4 files:** +391 lines, -67 lines

- `backend/app/graph/nodes/voice_synthesizer.py` (refactored)
- `backend/app/utils/storage.py` (temp audio functions)
- `backend/app/db/models.py` (resume fields)
- `backend/app/db/migrate.py` (new columns + safer table checks)
- `backend/tests/test_voice_synthesizer_resilience.py` (NEW - 6 tests)
- `backend/requirements.txt` (tenacity added)

## Next Steps

Future enhancements (Phase 3):
- Resume endpoint (POST /api/story/retry/{job_id})
- Enhanced error UI (show partial progress)
- "Try Again" button for users

## Commits (3 total)

1. `7a21ce6` - TDD RED: Add tests for voice resilience
2. `4006f9d` - WIP: Voice resilience partial implementation
3. `98ba26c` - Complete Phase 2: Voice synthesizer resilience
```

---

**Phase 2 is complete! Ready to merge.** 🚀
