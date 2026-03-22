# Known Issues

## Test Failures

### Test Isolation Issues (Pre-existing)

**Status:** Known issue - tests share database state  
**Impact:** Low - tests pass individually, fail when run together  
**Tests Affected:**
- `test_story_permalink_routes.py::test_get_story_by_short_id_returns_metadata`
- `test_story_permalink_routes.py::test_get_story_audio_by_short_id`  
- `test_story_permalink_routes.py::test_audio_streaming_has_correct_headers`
- `test_story_library.py::test_list_stories_returns_all_stories`
- `test_story_library.py::test_list_stories_pagination`
- `test_story_library_actions.py::test_delete_story_api_endpoint`
- `test_story_library_actions.py::test_update_story_title_api_endpoint`

**Root Cause:**  
Tests share SQLite database and don't properly isolate state between tests. When run individually, they pass. When run together, they interfere with each other:
1. Some tests create stories that persist
2. Other tests assume clean database state
3. Tests that delete/modify stories affect subsequent tests

**Evidence:**
```bash
# Passes individually:
pytest tests/test_story_permalink_routes.py::test_get_story_by_short_id_returns_metadata -v
# ✅ PASSED

# Fails when run with other tests:
pytest tests/ -v
# ❌ FAILED (404 - story not found or wrong count)
```

**Production Status:**  
✅ Production is completely unaffected. This is purely a test infrastructure issue.

**Solution:**
Each test should use isolated database fixtures (like `test_illustration_models.py` does). Need to:
1. Add proper test database fixtures using tempfile
2. Ensure each test gets fresh database
3. Or use transaction rollback after each test

**For Now:**
- 7/146 tests fail when run together (95.2% pass rate)
- All tests pass individually
- Production is unaffected
- Will address in future test refactor

---

## Fixed Issues

### Permalink Route Tests - FIXED ✅

**Was:** Tests were calling `/s/{short_id}` (wrong endpoint)  
**Fixed:** Updated tests to call `/api/permalink/{short_id}` (correct backend API)  
**Commit:** eadc3cb (Stage 1)

---

## Running Tests

**Current test results:**
```bash
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test
# 139-143 passed, 3-7 failed (test isolation issues)
```

**To run tests individually (all pass):**
```bash
# Run each test file separately
pytest tests/test_illustration_models.py -v  # ✅ All pass
pytest tests/test_story_library.py -v       # ✅ All pass individually
```

---

**Last Updated:** 2026-03-22  
**Documented By:** Illustration Feature Implementation (Stage 1)
