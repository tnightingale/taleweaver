# Shared Job State - Remaining Work

**Status:** Foundation Complete (JobState model + CRUD)  
**Remaining:** Replace in-memory jobs dict in routes/story.py

---

## ✅ Completed (Committed)

1. ✅ JobState database model created
2. ✅ Auto-migration script (creates job_state table)
3. ✅ 7 CRUD functions implemented:
   - create_job_state()
   - get_job_state()
   - update_job_stage()
   - update_job_progress()
   - mark_job_complete()
   - mark_job_failed()
   - cleanup_old_jobs()
4. ✅ 11 tests passing (TDD RED → GREEN)
5. ✅ Migration integrated into startup

---

## 🔄 Remaining Work (2-3 hours)

### Replace in-memory jobs dict with database calls

**File:** `backend/app/routes/story.py`

**20 replacements needed:**

#### 1. Remove cleanup function (line 29-40)
```python
# DELETE:
def _cleanup_old_jobs():
    ...del jobs[jid]...

# Already have: cleanup_old_jobs() in CRUD
```

#### 2. Update create_custom_story (lines 192-207)
```python
# REPLACE:
jobs[job_id] = {"status": "processing", ...}
jobs[job_id]["_task"] = task

# WITH:
from app.db.crud import create_job_state
db = SessionLocal()
try:
    create_job_state(db, job_id, stages)
finally:
    db.close()

asyncio.create_task(run_pipeline(job_id, state))  # Don't store task
```

#### 3. Update create_historical_story (lines 251-266)
Same changes as create_custom_story

#### 4. Update run_pipeline (lines 98-170)
```python
# ADD at start:
from app.db.crud import update_job_stage, mark_job_complete, mark_job_failed
from app.db.database import SessionLocal
db = SessionLocal()

# REPLACE:
jobs[job_id]["current_stage"] = "writing"
# WITH:
update_job_stage(db, job_id, "writing")

# REPLACE (line 109):
jobs[job_id]["current_stage"] = next_stage
# WITH:
update_job_stage(db, job_id, next_stage)

# REPLACE (lines 117-124):
jobs[job_id]["status"] = "complete"
jobs[job_id]["title"] = ...
jobs[job_id]["short_id"] = ...
# WITH:
mark_job_complete(db, job_id, title=..., short_id=..., ...)

# REPLACE (lines 169-170):
jobs[job_id]["status"] = "failed"
jobs[job_id]["error"] = ...
# WITH:
mark_job_failed(db, job_id, error_message)

# ADD at end:
finally:
    db.close()
```

#### 5. Update get_job_status (lines 304-359)
```python
# ADD:
from app.db.crud import get_job_state
db = SessionLocal()
try:
    job = get_job_state(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    # REPLACE all job["field"] with job.field
    # job["status"] → job.status
    # job["title"] → job.title
    # job.get("scenes") → json.loads(job.scenes_json) if job.scenes_json else None
    
finally:
    db.close()
```

#### 6. Update get_audio endpoint (lines 361-389)
```python
# REPLACE entire function:
# Instead of reading from jobs dict (final_audio)
# Read from saved story file:

from app.db.crud import get_story_by_id
db = SessionLocal()
try:
    story = get_story_by_id(db, job_id)
    if not story:
        raise HTTPException(404, "Story not found")
    
    return FileResponse(
        path=story.audio_path,
        media_type="audio/mpeg"
    )
finally:
    db.close()
```

---

## Testing Checklist

After making changes:

- [ ] Run all tests: `pytest tests/ -v`
- [ ] Verify 185+ tests pass
- [ ] Build Docker image
- [ ] Run with gunicorn 4 workers
- [ ] Create story and poll status
- [ ] Verify no "job not found" errors
- [ ] Generate 2 stories concurrently
- [ ] Both should complete successfully

---

## Estimated Time

- Replace jobs dict: 2-3 hours
- Testing & fixes: 1 hour
- **Total remaining: 3-4 hours**

---

## Why This Is Important

**Current Bug:**
- Gunicorn worker 1 creates job in its memory
- Worker 2 handles status poll → job not found!
- Results in "Whoops! Job not found" errors
- Story generation appears broken

**After Fix:**
- All workers share database
- Worker 1 creates job → stored in DB
- Worker 2 polls → reads from DB → works!
- Reliable story generation with multiple workers

---

**Foundation is ready. Routes replacement is mechanical but time-consuming.**
