# Known Issues

**Last Updated:** 2026-03-22

---

## ✅ All Fixed!

All known test issues have been resolved. All 146 tests now pass consistently.

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
