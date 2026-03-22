# Known Issues

## Test Failures

### Permalink Route Tests (Pre-existing)

**Status:** Known failing since commit e579082  
**Impact:** Low - doesn't affect production  
**Tests Affected:**
- `test_story_permalink_routes.py::test_get_story_by_short_id_returns_metadata`
- `test_story_permalink_routes.py::test_get_story_audio_by_short_id`  
- `test_story_permalink_routes.py::test_audio_streaming_has_correct_headers`

**Root Cause:**  
These are RED tests (TDD) that were never made GREEN. They test backend routes at `/s/{short_id}` which don't exist. The routing architecture is:
- `/s/*` → Frontend SPA (React Router handles story permalinks)
- `/api/permalink/{short_id}` → Backend API (actual working endpoint)

**Why They Fail:**
1. Tests call `GET /s/{short_id}` expecting backend JSON response
2. TestClient hits FastAPI app directly (no Caddy proxy)
3. Backend has no `/s/` routes, only `/api/permalink/` routes
4. Tests return 404

**Production Status:**  
✅ Production works fine! Frontend handles `/s/` routes via React Router, backend serves data via `/api/permalink/` endpoints.

**How to Verify Production Works:**
```bash
# These work in production (through Caddy + React Router):
curl http://taleweaver.lan/s/kor3k72n  # Returns HTML (SPA)
curl http://taleweaver.lan/api/permalink/kor3k72n  # Returns JSON

# But in tests (TestClient, no Caddy):
client.get("/s/kor3k72n")  # 404 - no backend route
client.get("/api/permalink/kor3k72n")  # 200 - works!
```

**Solution Options:**
1. **Option A (Quick):** Update tests to use `/api/permalink/` instead of `/s/`
2. **Option B (Correct):** Add backend `/s/` routes that delegate to `/api/permalink/` for TestClient compatibility
3. **Option C (Best):** Move these to frontend E2E tests where full routing stack is available

**For Now:**
- Tests are expected to fail (3/146 = 97.9% pass rate)
- Production is unaffected
- Will address in future refactor

---

## Running Tests

**Expected test results:**
```bash
docker compose run --rm backend-test
# 143 passed, 3 failed (permalink tests)
```

**To run only passing tests:**
```bash
docker compose run --rm backend-test sh -c \
  "pytest tests/ --ignore=tests/test_story_permalink_routes.py"
```

---

**Last Updated:** 2026-03-22  
**Documented By:** Illustration Feature Implementation (Stage 1)
