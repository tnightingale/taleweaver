# PR: Fix Illustration Generator Resilience

**Branch:** `fix/illustration-resilience` ✅ (pushed)  
**Create PR at:** https://github.com/tnightingale/taleweaver/pull/new/fix/illustration-resilience

---

## PR Title

```
Fix: Illustration generator partial failure handling (only 1 image bug)
```

## PR Description

```markdown
## Summary

Fixes critical production bug where only the first illustration generates, leaving stories with 1 of 8 images. Implements per-image error handling, detailed logging, and partial result preservation.

**Bug Fixed:** 🔴 CRITICAL
- Only first illustration was generating in production
- Loop stopped after first image with no error logs
- Users saw stories with `has_illustrations: true` but only 1 image displaying
- 7 images worth of Google API quota wasted

**Example affected story:** http://taleweaver.lan/story/aa0a8b72-f68f-40e7-8eaf-2b65db1993e4

## Problem

**Root Cause:**
```python
# OLD: Single try/except around entire loop
try:
    for i, scene in enumerate(scenes):
        image_bytes = await provider.generate_image(...)
        scene["image_url"] = image_url  # Mutates in-place
        
except Exception as e:
    logger.error(f"Illustration generation failed: {e}")
    return {"scenes": scenes}  # ← Only scene[0] was updated before exception!
```

**Timeline from production logs:**
```
18:27:26 - ✅ Illustration 1/8 generated
18:27:42 - 🛑 Loop stops (no logs for images 2-8)
18:28:02 - Story completes with only 1 image
```

**Issue:** Exception after image 1 broke the loop. Only scene[0] had image_url populated. Scenes 1-7 remained null.

## Solution

**Per-Image Error Handling:**
```python
# NEW: try/except inside loop
successful_count = 0
failed_count = 0
errors = []

for i, scene in enumerate(scenes):
    try:
        image_bytes = await provider.generate_image(...)
        scene["image_url"] = image_url
        scene["generation_metadata"]["succeeded"] = True
        successful_count += 1
        
    except Exception as e:
        logger.exception(f"❌ Failed illustration {i+1}")
        scene["image_url"] = None
        scene["generation_metadata"] = {"succeeded": False, "error": str(e)}
        failed_count += 1
        errors.append({"index": i, "error": str(e)})
        continue  # ← CONTINUE to next image!

# Return partial results
return {
    "scenes": scenes,  # Has mixed success/failure
    "partial_illustrations": True,
    "successful_count": 4,  # e.g., 4 of 8
    "failed_count": 4,
    "errors": [...]
}
```

## Changes

### 1. Illustration Generator Refactor

**File:** `backend/app/graph/nodes/illustration_generator.py`

**Key Changes:**
- ✅ Move try/except **inside** loop (per-image granularity)
- ✅ `continue` on error (don't break loop - try remaining images)
- ✅ Track `successful_count` and `failed_count`
- ✅ Build `errors` list with detailed info per failure
- ✅ Use `logger.exception()` for full traceback
- ✅ Add `succeeded: true/false` to generation_metadata
- ✅ Return partial results with `partial_illustrations: true` flag

**Benefits:**
- Stories can have 3 of 8 illustrations (better than 0!)
- Transient failures don't stop entire generation
- Detailed error tracking per image
- Metadata shows which images succeeded vs. failed

### 2. Enhanced Provider Logging

**File:** `backend/app/services/illustration/nanobanana.py`

**Key Changes:**
- ✅ Use `logger.exception()` instead of `logger.error()`
- ✅ Log error type, message, prompt length, model
- ✅ Log reference image URL if present
- ✅ Detect and flag specific error types:
  - 🔴 Quota exceeded
  - 🔴 Rate limit (429)  
  - 🔴 Auth errors (401/403)

**Benefits:**
- Easier debugging of production issues
- Clear indication of root cause (quota vs. rate limit vs. auth)
- Full context for investigation

## Test Results

```
✅ 159/159 tests passing (100%)
✅ 5 new tests (TDD: RED → GREEN)
```

**New Tests:**
1. `test_illustration_generator_continues_after_single_failure`
   - Simulates failure at image 2 of 5
   - Verifies images 0,1,3,4 succeed (loop continues)
   - Verifies image 2 has null image_url

2. `test_illustration_generator_tracks_each_error`
   - Simulates failures at images 1 and 3
   - Verifies errors list has 2 entries with details

3. `test_illustration_generator_complete_failure`
   - All images fail
   - Verifies graceful handling (returns error, doesn't crash)

4. `test_illustration_generator_logs_detailed_errors`
   - Verifies error type and message are logged

5. `test_illustration_generator_preserves_successful_metadata`
   - Partial success (2 of 4 succeed)
   - Verifies metadata shows succeeded: true/false per image

## Docker Verification

```
✅ Container builds successfully
✅ Gunicorn starts (4 workers)
✅ Health endpoint responds
✅ All tests passing in container
```

## Expected Impact

**Before:**
- Story generates → First illustration succeeds → Second fails silently → Loop stops
- Result: 1 of 8 images (12.5% success rate)
- Logs: Single generic error, no details

**After:**
- Story generates → Images 1,2,3 succeed → Image 4 fails → Images 5,6,7,8 continue
- Result: 7 of 8 images (87.5% success rate) - partial success!
- Logs: Detailed error for image 4 with type, message, context

## Next Steps

After this PR merges:
- Monitor production illustrations (should see >1 image per story)
- Check logs for detailed error info on failures
- Implement Phase 2 (voice synthesizer resilience) if needed
- Consider retry logic for transient errors

## Files Changed

**3 files:** +465 lines, -27 lines

- `backend/app/graph/nodes/illustration_generator.py` (refactored)
- `backend/app/services/illustration/nanobanana.py` (enhanced logging)
- `backend/tests/test_illustration_generator_resilience.py` (NEW - 5 tests)

## Commits (2 total)

1. `9c713e3` - TDD GREEN: Fix illustration generator to handle partial failures
2. `ddfc085` - Improve provider error logging for debugging
```

---

**This fixes the critical production bug! Ready to merge.** 🚀
