# Known Issues

**Last Updated:** 2026-03-22

---

## 🔴 Active Issues

### Issue 1: Only First Illustration Generates (2026-03-22) - ✅ FIXED

**Severity:** High  
**Affects:** Story generation with illustrations  
**Status:** ✅ FIXED - Merged to main  
**Fix Deployed:** Pending Once auto-update

**Symptom:**
- Story generation with illustrations only produces first image
- Scenes 1-7 have `image_url: null` in database
- Only scene_0.png exists on filesystem
- No error logs visible

**Example:** http://taleweaver.lan/story/aa0a8b72-f68f-40e7-8eaf-2b65db1993e4

**Evidence:**
```
Timeline from logs:
18:27:07 - illustration_generator starts (parallel with voice synthesis)
18:27:26 - Illustration 1/8 generated ✅ (scene_0.png saved)
18:27:42 - audio_stitcher starts (voice synthesis complete)
         - illustration_generator should still be running...
         - but NO logs for illustrations 2-8
         - NO error logs
18:27:54 - Stage label "generating_illustrations" (misleading - already done)
18:28:02 - Pipeline completes

API Response:
- has_illustrations: true
- scenes[0].image_url: "/storage/.../scene_0.png" ✅
- scenes[1-7].image_url: null ❌
```

**Possible Causes:**
1. **Google API quota/rate limit** - First succeeds, rest fail silently
2. **Exception caught without logging** - try/except in illustration_generator
3. **Image-to-image reference not working** - reference_image_url causes silent failure  
4. **Async loop issue** - await in loop not working as expected
5. **Provider returning early** - generate_image() failing after first call

**Investigation Needed:**
- [ ] Add verbose logging in illustration_generator loop
- [ ] Log each Google API call attempt
- [ ] Catch and log exceptions per-image (not whole loop)
- [ ] Test with 2-3 images instead of 8
- [ ] Check Google API error responses

**Workaround:**
- Stories still work (audio + transcript + 1 image)
- Disable illustrations: `ILLUSTRATION_PROVIDER=none`

**Priority:** High - Degrades feature value

---

## ✅ Resolved Issues

---

## Fixed Issues Archive

### Test Isolation Issues - FIXED ✅ (2026-03-22)

**Was:** Tests shared database state causing failures when run together  
**Impact:** 7 tests failed when run together, passed individually  
**Fixed:** Added `conftest.py` with isolated `test_db` and `test_client` fixtures  
**Solution:**
- Created shared `test_db` fixture that creates temporary database per test
- Created `test_client` fixture that depends on `test_db` for same-database access
- Updated all tests to use fixtures instead of global `SessionLocal()` and `client`
- Added `test_db.expire_all()` where needed to refresh session cache

**Commits:**
- Added conftest.py with isolated fixtures
- Updated test_story_permalink_routes.py to use fixtures
- Updated test_story_library.py to use fixtures
- Updated test_story_library_actions.py to use fixtures

### Permalink Route Tests - FIXED ✅ (2026-03-22)

**Was:** Tests were calling `/s/{short_id}` (frontend route)  
**Fixed:** Updated tests to call `/api/permalink/{short_id}` (backend API)  
**Commit:** 1f350db

---

## Running Tests

**Current test results:**
```bash
COMPOSE_PROFILES=test docker compose -f docker-compose.dev.yml run --rm backend-test
# ✅ 146 passed, 0 failed
```

**GitHub Actions CI:**
```bash
# CI runs automatically on push to main and feature branches
# Check status: https://github.com/YOUR_ORG/taleweaver/actions
```

---

## Test Best Practices

### Writing New Tests

Always use isolated fixtures from `conftest.py`:

```python
def test_something(test_db):
    """Test that uses database"""
    story = save_story(db=test_db, ...)
    assert story.id is not None

def test_api_endpoint(test_db, test_client):
    """Test that uses API endpoints"""
    # Create data in test_db
    story = save_story(db=test_db, ...)
    
    # Call API endpoint
    response = test_client.get("/api/stories")
    
    # Verify response
    assert response.status_code == 200
    
    # If checking database after API call, refresh session cache
    test_db.expire_all()
    updated = get_story_by_id(test_db, story.id)
```

### Don't Do This:
```python
# ❌ Don't use global SessionLocal()
db = SessionLocal()
story = save_story(db=db, ...)
db.close()

# ❌ Don't use global TestClient
client = TestClient(app)
response = client.get("/api/stories")
```

---

**Last Updated:** 2026-03-22  
**All Issues Resolved:** Yes
