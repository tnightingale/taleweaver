# Shared Job State for Gunicorn Workers

**Feature:** Fix Multi-Worker Job State Sharing  
**Created:** 2026-03-22  
**Status:** 🔴 CRITICAL BUG  
**Priority:** HIGH  
**Estimated Time:** 4-8 hours (varies by approach)

---

## Problem Statement

### Critical Bug

**Symptom:**
- "Whoops! Job not found" error during story generation
- Story generation appears to hang indefinitely
- Random failures when polling job status

**Root Cause:**
- Gunicorn runs with 4 workers (separate processes)
- Each worker has its own Python interpreter and memory space
- In-memory `jobs` dict in `backend/app/routes/story.py` is per-worker
- Worker 1 creates job → stores in its `jobs` dict
- Worker 2 handles status poll → checks its `jobs` dict → not found!

**Current Code:**
```python
# backend/app/routes/story.py
jobs: dict[str, dict] = {}  # ← This is PER-WORKER, not shared!
```

**Impact:**
- 🔴 **CRITICAL** - Story generation is broken in production
- Users can't generate stories reliably
- Affects all story types (custom + historical)
- Affects both illustrated and non-illustrated stories

---

## Current Workaround

**Temporary Fix:** Revert to single uvicorn worker
- Works but defeats the purpose of multi-worker setup
- Can't handle concurrent story generations
- App hangs when generating story (blocks all requests)

**Status:** NOT ACCEPTABLE for production

---

## Research Findings

### Worker State Sharing Options

**1. SQLite Database (Simplest)**
- Store job state in database table
- Query on each status check
- Pros: Already have SQLite, no new dependencies
- Cons: Polling overhead, not ideal for rapidly changing state

**2. Redis (Industry Standard)**
- In-memory key-value store
- Fast reads/writes (~1ms)
- Pub/sub for real-time updates
- Pros: Fast, battle-tested, supports expiration
- Cons: New dependency, requires Redis server

**3. Filesystem (Low-Tech)**
- Store job state as JSON files in `/storage/jobs/{job_id}.json`
- Read/write on demand
- Pros: No new dependencies, simple
- Cons: File I/O slower than memory, no atomic operations

**4. Celery/ARQ/RQ (Full Job Queue)**
- Dedicated task queue systems
- Pros: Built for this purpose, retries, monitoring
- Cons: Overkill for our use case, heavy dependencies

**5. Shared Memory (multiprocessing)**
- Use Python's multiprocessing.Manager
- Pros: Built-in, no dependencies
- Cons: Doesn't work with gunicorn's pre-fork model

---

## Implementation Options

### Option A: SQLite Job State Table (Recommended)

**Approach:** Store job state in database, query on each request.

**Pros:**
- ✅ No new dependencies (SQLite already used)
- ✅ Persistent (survives restarts)
- ✅ Simple to implement
- ✅ Atomic updates via SQL transactions
- ✅ Works with any number of workers
- ✅ Can add indexes for performance

**Cons:**
- ❌ Slower than in-memory (but likely fine, ~5ms per query)
- ❌ More database writes during generation
- ❌ Need to clean up old jobs

**Architecture:**

**New Table:**
```sql
CREATE TABLE job_state (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,  -- 'processing', 'complete', 'failed'
    current_stage TEXT,
    stages TEXT,  -- JSON array
    progress REAL DEFAULT 0.0,
    progress_detail TEXT,
    title TEXT,
    duration_seconds INTEGER,
    audio_data BLOB,  -- Temporary until saved to file
    transcript TEXT,
    art_style TEXT,
    scenes_json TEXT,  -- JSON
    short_id TEXT,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_status ON job_state(status);
CREATE INDEX idx_job_created ON job_state(created_at);
```

**Implementation:**

**1. Create JobState CRUD:**
```python
# backend/app/db/crud.py

def create_job(db: Session, job_id: str, stages: list[str]) -> JobState:
    job = JobState(
        job_id=job_id,
        status='processing',
        current_stage='writing',
        stages=json.dumps(stages),
        created_at=datetime.utcnow()
    )
    db.add(job)
    db.commit()
    return job

def get_job(db: Session, job_id: str) -> Optional[JobState]:
    return db.query(JobState).filter(JobState.job_id == job_id).first()

def update_job_stage(db: Session, job_id: str, stage: str, progress: float = None):
    job = get_job(db, job_id)
    if job:
        job.current_stage = stage
        if progress is not None:
            job.progress = progress
        job.updated_at = datetime.utcnow()
        db.commit()

def mark_job_complete(db: Session, job_id: str, title: str, duration: int, ...):
    job = get_job(db, job_id)
    if job:
        job.status = 'complete'
        job.title = title
        job.duration_seconds = duration
        # ... set other fields
        db.commit()
```

**2. Replace In-Memory Dict:**
```python
# backend/app/routes/story.py

# REMOVE: jobs: dict[str, dict] = {}

# Replace all jobs[job_id] access with database calls:
@router.post("/custom")
async def create_custom_story(request: CustomStoryRequest):
    job_id = str(uuid.uuid4())
    
    db = SessionLocal()
    try:
        create_job(db, job_id, stages)
    finally:
        db.close()
    
    # ... rest of function

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    db = SessionLocal()
    try:
        job = get_job(db, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        
        if job.status == "complete":
            return JobCompleteResponse(...)
        return JobStatusResponse(...)
    finally:
        db.close()
```

**3. Update Pipeline Tracking:**
```python
async def run_pipeline(job_id: str, state: dict):
    try:
        db = SessionLocal()
        
        async for event in pipeline.astream(state):
            # Update stage in database
            update_job_stage(db, job_id, next_stage, progress)
        
        # Mark complete
        mark_job_complete(db, job_id, ...)
    finally:
        db.close()
```

**Estimated Time:** 4-5 hours  
**Complexity:** Medium  
**Best For:** Quick fix, leverages existing infrastructure

---

### Option B: Redis Job State (Best Performance)

**Approach:** Use Redis for fast in-memory job state with multi-worker support.

**Pros:**
- ✅ Very fast (~1ms reads/writes)
- ✅ Built for this use case
- ✅ Atomic operations
- ✅ TTL/expiration built-in
- ✅ Pub/sub for real-time updates (future)

**Cons:**
- ❌ New dependency (Redis server)
- ❌ More infrastructure to manage
- ❌ Overkill for current needs

**Architecture:**

**Redis Structure:**
```
job:{job_id}:status       → "processing"
job:{job_id}:stage        → "synthesizing"
job:{job_id}:progress     → "45.5"
job:{job_id}:data         → JSON blob with full state
```

**Implementation:**
```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def create_job(job_id: str, stages: list):
    redis_client.hset(f"job:{job_id}", mapping={
        "status": "processing",
        "current_stage": "writing",
        "stages": json.dumps(stages),
        "created_at": datetime.utcnow().isoformat()
    })
    redis_client.expire(f"job:{job_id}", 3600)  # 1 hour TTL

def get_job(job_id: str) -> dict:
    data = redis_client.hgetall(f"job:{job_id}")
    if not data:
        return None
    return {k.decode(): v.decode() for k, v in data.items()}
```

**Docker Compose:**
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
  
  backend:
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379/0
```

**Estimated Time:** 6-8 hours (including Docker setup)  
**Complexity:** Medium-High  
**Best For:** Long-term scalability, best performance

---

### Option C: Filesystem Job State (Quick Fix)

**Approach:** Store job state as JSON files in `/storage/jobs/`.

**Pros:**
- ✅ No new dependencies
- ✅ Simple to implement (2-3 hours)
- ✅ Persistent across restarts
- ✅ Easy to debug (can view files)

**Cons:**
- ❌ Slower than memory (file I/O)
- ❌ No atomic operations (race conditions possible)
- ❌ Manual cleanup required

**Implementation:**
```python
import json
from pathlib import Path

JOBS_DIR = Path("/storage/jobs")
JOBS_DIR.mkdir(exist_ok=True)

def save_job(job_id: str, data: dict):
    job_file = JOBS_DIR / f"{job_id}.json"
    with open(job_file, 'w') as f:
        json.dump(data, f)

def load_job(job_id: str) -> Optional[dict]:
    job_file = JOBS_DIR / f"{job_id}.json"
    if not job_file.exists():
        return None
    with open(job_file, 'r') as f:
        return json.load(f)

def update_job(job_id: str, updates: dict):
    job = load_job(job_id)
    if job:
        job.update(updates)
        save_job(job_id, job)
```

**Estimated Time:** 2-3 hours  
**Complexity:** Low  
**Best For:** Quick fix, minimal changes

---

### Option D: Hybrid - Database + In-Memory Cache

**Approach:** Use database as source of truth, cache in memory per-worker.

**Pros:**
- ✅ Fast reads (from cache when available)
- ✅ Reliable (database is source of truth)
- ✅ No new dependencies

**Cons:**
- ❌ More complex
- ❌ Cache invalidation complexity
- ❌ Not worth the complexity

**Not Recommended** - Over-engineered for this use case

---

## Recommended Approach: **Option A (SQLite Job State)**

### Why SQLite?

1. **Already have it** - No new infrastructure
2. **Good enough performance** - 5-10ms queries acceptable for polling
3. **Simple** - Leverages existing database patterns
4. **Persistent** - Jobs survive restarts
5. **Atomic** - SQL transactions prevent race conditions
6. **Scalable enough** - Can handle current load easily

### Why NOT Redis?

- Adds infrastructure complexity
- Requires Docker Compose changes
- Overkill for current scale (few concurrent jobs)
- Can migrate to Redis later if needed

### Why NOT Filesystem?

- Race conditions without locking
- Slower than database
- No atomicity guarantees

---

## Implementation Plan - Option A (SQLite)

### Stage 1: Create Job State Table (1-2 hours)

#### Tasks

**1.1 Create JobState Model**
- [ ] Create `backend/app/db/models.py` - Add JobState model:
  ```python
  class JobState(Base):
      __tablename__ = "job_state"
      
      job_id = Column(String, primary_key=True)
      status = Column(String, nullable=False)  # processing, complete, failed
      current_stage = Column(String)
      stages = Column(Text)  # JSON array
      progress = Column(Float, default=0.0)
      progress_detail = Column(String)
      
      # Story data (while processing)
      title = Column(String)
      duration_seconds = Column(Integer)
      audio_data = Column(LargeBinary)  # Temporary storage
      transcript = Column(Text)
      art_style = Column(String)
      scenes_json = Column(Text)  # JSON
      short_id = Column(String)
      
      # Error tracking
      error_message = Column(Text)
      
      # Timestamps
      created_at = Column(DateTime, default=datetime.utcnow)
      updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
      
      __table_args__ = (
          Index('idx_job_status', 'status'),
          Index('idx_job_created', 'created_at'),
      )
  ```

**1.2 Add to Auto-Migration**
- [ ] Update `backend/app/db/migrate.py`:
  ```python
  def run_migrations():
      # ... existing migrations
      
      # Create job_state table if not exists
      conn.execute('''
          CREATE TABLE IF NOT EXISTS job_state (
              job_id TEXT PRIMARY KEY,
              status TEXT NOT NULL,
              current_stage TEXT,
              ...
          )
      ''')
  ```

**1.3 Create CRUD Functions**
- [ ] Add to `backend/app/db/crud.py`:
  - `create_job_state(db, job_id, stages) -> JobState`
  - `get_job_state(db, job_id) -> Optional[JobState]`
  - `update_job_stage(db, job_id, stage, progress)`
  - `update_job_progress(db, job_id, progress, detail)`
  - `mark_job_complete(db, job_id, ...)`
  - `mark_job_failed(db, job_id, error)`
  - `cleanup_old_jobs(db, max_age_hours=24)`

**Tests:**
- [ ] Test job creation
- [ ] Test job retrieval
- [ ] Test stage updates
- [ ] Test concurrent updates (simulate workers)
- [ ] Test cleanup

---

### Stage 2: Replace In-Memory Jobs Dict (2-3 hours)

#### Tasks

**2.1 Update Story Creation Endpoints**
- [ ] In `create_custom_story`:
  ```python
  # REMOVE: jobs[job_id] = {...}
  
  # ADD:
  db = SessionLocal()
  try:
      create_job_state(db, job_id, stages)
  finally:
      db.close()
  ```
- [ ] In `create_historical_story`: Same change
- [ ] Remove `_cleanup_old_jobs()` calls (will use DB cleanup)

**2.2 Update Job Status Endpoint**
- [ ] In `get_job_status`:
  ```python
  # REMOVE: if job_id not in jobs...
  
  # ADD:
  db = SessionLocal()
  try:
      job = get_job_state(db, job_id)
      if not job:
          raise HTTPException(404, "Job not found")
      
      if job.status == "complete":
          return JobCompleteResponse(
              job_id=job.job_id,
              status="complete",
              title=job.title,
              duration_seconds=job.duration_seconds,
              audio_url=f"/api/story/audio/{job_id}",
              transcript=job.transcript,
              short_id=job.short_id,
              permalink=f"/s/{job.short_id}",
              has_illustrations=bool(job.scenes_json),
              art_style=job.art_style,
              scenes=json.loads(job.scenes_json) if job.scenes_json else None
          )
      
      return JobStatusResponse(
          job_id=job.job_id,
          status=job.status,
          current_stage=job.current_stage,
          progress=job.progress or 0,
          total_segments=0,  # Deprecated
          error=job.error_message or ""
      )
  finally:
      db.close()
  ```

**2.3 Update Audio Endpoint**
- [ ] Store audio in job_state temporarily
- [ ] Or store in filesystem immediately (better)
- [ ] Return from job_state.audio_data or file

**2.4 Update run_pipeline Function**
- [ ] Remove all `jobs[job_id][...]` accesses
- [ ] Replace with database calls:
  ```python
  async def run_pipeline(job_id: str, state: dict):
      db = SessionLocal()
      
      try:
          # Update stage on each node completion
          async for event in pipeline.astream(state):
              for node_name in event:
                  next_stage = get_next_stage(node_name)
                  update_job_stage(db, job_id, next_stage)
                  final_state.update(event[node_name])
          
          # Mark complete
          mark_job_complete(
              db, job_id,
              title=final_state["title"],
              duration=final_state["duration_seconds"],
              transcript=final_state.get("story_text", ""),
              scenes_json=json.dumps(final_state.get("scenes"))
          )
          
      except Exception as e:
          mark_job_failed(db, job_id, str(e))
      finally:
          db.close()
  ```

**2.5 Add Periodic Cleanup**
- [ ] Create cleanup task (runs periodically):
  ```python
  @app.on_event("startup")
  async def start_cleanup_task():
      async def cleanup_loop():
          while True:
              await asyncio.sleep(3600)  # Every hour
              db = SessionLocal()
              try:
                  cleanup_old_jobs(db, max_age_hours=24)
              finally:
                  db.close()
      
      asyncio.create_task(cleanup_loop())
  ```

**Tests:**
- [ ] Test job creation and retrieval across "workers" (separate test runs)
- [ ] Test status polling finds job created by different "worker"
- [ ] Test concurrent pipeline execution (2 jobs at once)
- [ ] Test cleanup doesn't delete active jobs
- [ ] Test error handling (job not found, database errors)

---

### Stage 3: Optimize Performance (1 hour)

#### Tasks

**3.1 Add Database Indexes**
- [ ] Index on status (for filtering active jobs)
- [ ] Index on created_at (for cleanup queries)
- [ ] Verify query performance with EXPLAIN

**3.2 Optimize Hot Paths**
- [ ] Cache job_id in asyncio context for pipeline updates
- [ ] Batch updates where possible (stage + progress in one query)
- [ ] Use SELECT FOR UPDATE if concurrent updates needed

**3.3 Monitor Performance**
- [ ] Log query times for job operations
- [ ] Check for slow queries (>50ms)
- [ ] Optimize if needed

---

### Stage 4: Migration & Deployment (1 hour)

#### Tasks

**4.1 Database Migration**
- [ ] Add CREATE TABLE to migrate.py
- [ ] Test migration on fresh database
- [ ] Test migration on existing database

**4.2 Update Docker Entrypoint**
- [ ] Keep gunicorn with 4 workers (don't revert!)
- [ ] Ensure migration runs before workers start
- [ ] Test container startup

**4.3 Production Deployment**
- [ ] Deploy to production
- [ ] Monitor for errors
- [ ] Test job creation + status polling
- [ ] Generate test story end-to-end

---

## Alternative: Option C (Filesystem) - Quick Fix

If time is critical, filesystem approach can be implemented in 2-3 hours:

**Quick Implementation:**
```python
JOBS_DIR = Path("/storage/jobs")

def save_job_state(job_id: str, state: dict):
    (JOBS_DIR / f"{job_id}.json").write_text(json.dumps(state))

def load_job_state(job_id: str) -> Optional[dict]:
    path = JOBS_DIR / f"{job_id}.json"
    return json.loads(path.read_text()) if path.exists() else None

# Replace: jobs[job_id] = {...}
# With: save_job_state(job_id, {...})

# Replace: jobs[job_id]
# With: load_job_state(job_id)
```

**Pros:**
- Fastest to implement
- No new infrastructure

**Cons:**
- Not as robust as database
- Manual locking needed for atomicity

---

## Testing Strategy

### Unit Tests
```python
def test_job_state_shared_between_workers(test_db):
    # Worker 1 creates job
    create_job_state(test_db, "test-job", ["writing", "stitching"])
    
    # Simulate worker 2 querying (new session)
    db2 = SessionLocal()
    try:
        job = get_job_state(db2, "test-job")
        assert job is not None
        assert job.status == "processing"
    finally:
        db2.close()

def test_concurrent_job_updates():
    # Multiple workers updating same job
    # Verify no data loss
    pass
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_story_generation_with_workers(test_client, test_db):
    # Create story
    response = test_client.post("/api/story/custom", json={...})
    job_id = response.json()["job_id"]
    
    # Poll status (simulating different worker)
    response = test_client.get(f"/api/story/status/{job_id}")
    assert response.status_code == 200
```

### Manual Testing
- [ ] Build Docker image
- [ ] Run with 4 workers
- [ ] Create story in browser
- [ ] Poll status (verify no "job not found")
- [ ] Generate multiple stories concurrently
- [ ] Verify all complete successfully

---

## Success Criteria

- [ ] Story creation works reliably with 4 workers
- [ ] No "job not found" errors
- [ ] Status polling finds jobs created by other workers
- [ ] Multiple concurrent story generations work
- [ ] Jobs persist across container restarts (bonus)
- [ ] Cleanup removes old jobs properly
- [ ] Performance acceptable (<10ms overhead per status check)

---

## Migration Path

**Immediate (Option A):**
1. Implement SQLite job state (4-5 hours)
2. Deploy and test
3. Monitor for issues
4. Iterate if needed

**Future (Option B - if needed):**
1. Add Redis to infrastructure
2. Migrate job state from SQLite to Redis
3. Gain performance benefits
4. Enable pub/sub for real-time updates

**Progressive enhancement approach** - Start simple, scale when needed

---

## Files to Create/Modify

**New:**
- `backend/app/db/models.py` - JobState model (add to existing)
- `backend/tests/test_job_state.py` - Job state tests

**Modified:**
- `backend/app/db/migrate.py` - Add job_state table creation
- `backend/app/db/crud.py` - Job state CRUD functions
- `backend/app/routes/story.py` - Replace jobs dict with DB calls
- `backend/app/main.py` - Add cleanup task
- `backend/tests/test_story_routes.py` - Update tests

**Total:** ~6 files, mostly replacing dict access with function calls

---

## Risks & Mitigations

**Risk 1: Database performance bottleneck**
- Mitigation: Add indexes, monitor query times
- Mitigation: Optimize hot paths (batch updates)
- Mitigation: Can migrate to Redis later if needed

**Risk 2: Migration fails in production**
- Mitigation: Test migration thoroughly
- Mitigation: Backup database before deployment
- Mitigation: Can rollback to single worker if critical

**Risk 3: Concurrent write conflicts**
- Mitigation: Use SQLite WAL mode (already default)
- Mitigation: Separate reads from writes where possible
- Mitigation: Test concurrent updates

---

## Estimated Effort

| Stage | Time | Complexity |
|-------|------|------------|
| 1. Create job state table & model | 1-2h | Low |
| 2. Replace in-memory dict | 2-3h | Medium |
| 3. Performance optimization | 1h | Low |
| 4. Migration & deployment | 1h | Low |
| **Total** | **5-7h** | **Medium** |

---

## Priority

**🔴 CRITICAL** - Blocks story generation in production with multiple workers

**Must fix before:**
- Enabling gunicorn multi-worker in production
- Scaling to handle concurrent users
- Deploying enhanced progress indicator (needs shared state)

---

**Recommendation:** Implement **Option A (SQLite)** immediately (5-7 hours)  
**Future Enhancement:** Migrate to **Option B (Redis)** if scale requires it

Complete implementation plan with tasks, tests, and migration strategy included above.
