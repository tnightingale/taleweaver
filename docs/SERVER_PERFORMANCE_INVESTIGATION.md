# Server Performance Investigation - 2026-03-23

**Issue:** Server appears unresponsive during story generation  
**Status:** 🟡 INVESTIGATED - Not critical, but needs optimization

---

## Findings

### What's Working

**Gunicorn Configuration:** ✅ Correct
- 4 workers running
- UvicornWorker class (supports async)
- 600s timeout
- All workers initialize successfully

**Server Not Actually Hung:**
- Health endpoint responds (11ms)
- API endpoints respond (12ms)
- Story generation completes successfully
- Just SLOW to respond to HTTP requests during generation

---

### Root Cause Analysis

**NOT the API calls:**
- ✅ Google Gemini calls are async (run_in_executor)
- ✅ ElevenLabs calls are async (asyncio.to_thread)
- ✅ These run in background tasks

**Likely Culprits:**

#### 1. Database Operations in Pipeline Loop

**Current Pattern:**
```python
# In illustration_generator and voice_synthesizer
for i in range(len(items)):
    # ... generate item ...
    
    # Update progress - CREATES NEW DB CONNECTION EACH TIME!
    db = SessionLocal()  # New connection
    try:
        update_job_progress(db, job_id, progress, detail)
    finally:
        db.close()  # Close connection
```

**Problem:**
- Creates 20+ database connections during single job
- Each SessionLocal() is a NEW connection
- SQLite with multiple workers + many connections = potential locks
- Connection creation/teardown has overhead

**Impact:**
- Database operations might block worker threads
- Connection pool not configured (defaults to per-thread)
- WAL mode helps but not perfect with high write frequency

#### 2. Synchronous Database Operations in Async Context

**Current:**
- `update_job_progress()` is synchronous
- Called from async functions
- Not wrapped in `asyncio.to_thread()` or `run_in_executor()`
- Could block event loop

#### 3. Frontend Polling Frequency

**Current:**
- StoryRoute polls every 2 seconds
- InProgressJobs polls every 5 seconds
- If 2-3 tabs open = 4-6 requests/second
- Each request hits database
- Could contribute to load

---

## Reproduction

**When Server Appears Hung:**
- During illustration generation (long-running)
- When story is 50-80% complete
- Multiple status polls happening
- Database being updated frequently

**Symptoms:**
- Pages load slowly or timeout
- Health endpoint sometimes slow
- Not fully hung (eventually responds)

---

## Recommended Fixes

### Fix 1: Reduce Database Connection Churn (HIGH PRIORITY)

**Pass db session through instead of creating new ones:**

```python
# In run_pipeline:
async def run_pipeline(job_id: str, state: dict):
    db = SessionLocal()
    
    try:
        state["_db"] = db  # Pass to nodes
        
        # ... pipeline execution ...
    finally:
        db.close()

# In nodes:
async def voice_synthesizer(state: StoryState) -> dict:
    db = state.get("_db")  # Reuse existing session
    
    for i, segment in enumerate(segments):
        # ... synthesis ...
        
        if db and job_id:
            update_job_progress(db, job_id, progress, detail)
            # No db.close() here - managed by run_pipeline
```

**Benefits:**
- 1 database connection per job instead of 20+
- Fewer connection create/teardown operations
- Less lock contention

---

### Fix 2: Make Database Operations Async (MEDIUM PRIORITY)

**Wrap in executor:**
```python
async def update_job_progress_async(db, job_id, progress, detail):
    await asyncio.to_thread(update_job_progress, db, job_id, progress, detail)
```

**Benefits:**
- Doesn't block event loop
- Worker can handle other requests while DB operation completes

---

### Fix 3: Reduce Polling Frequency (LOW PRIORITY)

**Current:**
- 2 second interval

**Proposed:**
- 3-5 second interval (still feels responsive)
- Or adaptive: 2s during fast stages, 5s during slow stages

**Benefits:**
- Fewer database queries
- Less load on server

---

### Fix 4: Add Connection Pooling (FUTURE)

**Current:**
```python
engine = create_engine(SQLALCHEMY_DATABASE_URL)
```

**Proposed:**
```python
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

**Note:** SQLite doesn't benefit much from pooling (file-based), but helps manage connections

---

## Immediate Action

**Quick Win (15 minutes):**
- Fix 1: Pass db session through state
- Reduces connection churn by 95%

**Medium Term:**
- Fix 2: Make db operations async
- Fix 3: Adjust polling frequency

**Not Urgent:**
- Server IS responding (just slow)
- Jobs complete successfully
- Frontend fixes improve UX

---

## Workaround (Current)

**For Users:**
- Be patient during generation (5-10 min)
- Use InProgressJobs to navigate away safely
- Server will respond eventually

**For Developers:**
- Monitor but not critical
- Jobs complete successfully
- Not losing data

---

## Testing Needed

After implementing Fix 1:
- [ ] Generate 2 stories concurrently
- [ ] Monitor response times
- [ ] Check if unresponsiveness improves
- [ ] Verify no connection errors in logs

---

**Recommendation:** Implement Fix 1 (pass db session through) as quick improvement. Fixes 2-3 can wait.

**Priority:** Medium (annoying but not breaking functionality)
