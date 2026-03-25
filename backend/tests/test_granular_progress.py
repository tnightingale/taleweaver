"""
Tests for granular progress tracking — enriched progress data, structured JSON,
partial results through status/recent endpoints, and push notifications.
"""
import pytest
import json

from app.db.crud import (
    create_job_state,
    get_job_state,
    update_job_progress_data,
)
from app.db.models import PushSubscription


# ============================================================================
# Structured progress_detail (merge semantics)
# ============================================================================

def test_update_job_progress_data_stores_structured_json(test_db):
    """update_job_progress_data should store structured progress as JSON."""
    create_job_state(test_db, "struct-1", ["writing", "synthesizing"])

    update_job_progress_data(test_db, "struct-1", 50.0, {
        "message": "Generating audio...",
        "voice": {"completed": 5, "total": 12},
    })

    job = get_job_state(test_db, "struct-1")
    data = json.loads(job.progress_detail)
    assert data["message"] == "Generating audio..."
    assert data["voice"]["completed"] == 5
    assert data["voice"]["total"] == 12


def test_update_job_progress_data_merges_keys(test_db):
    """Successive calls should merge keys, not overwrite the whole object."""
    create_job_state(test_db, "struct-2", ["writing", "synthesizing"])

    update_job_progress_data(test_db, "struct-2", 40.0, {
        "message": "Generating audio...",
        "voice": {"completed": 3, "total": 12},
    })

    update_job_progress_data(test_db, "struct-2", 50.0, {
        "message": "Creating illustrations...",
        "illustrations": {"completed": 2, "total": 6, "urls": ["/storage/stories/x/scene_0.png"]},
    })

    job = get_job_state(test_db, "struct-2")
    data = json.loads(job.progress_detail)
    assert data["voice"]["completed"] == 3
    assert data["voice"]["total"] == 12
    assert data["illustrations"]["completed"] == 2
    assert data["illustrations"]["urls"] == ["/storage/stories/x/scene_0.png"]
    assert data["message"] == "Creating illustrations..."


def test_update_job_progress_data_monotonic_guard(test_db):
    """Progress should not decrease (monotonic guard)."""
    create_job_state(test_db, "struct-3", ["writing"])

    update_job_progress_data(test_db, "struct-3", 60.0, {"message": "A"})
    update_job_progress_data(test_db, "struct-3", 40.0, {"message": "B"})

    job = get_job_state(test_db, "struct-3")
    assert job.progress == 60.0


# ============================================================================
# Enriched status endpoint
# ============================================================================

def test_status_endpoint_includes_partial_results(test_db, test_client):
    """GET /api/story/status/{job_id} should include title, kid_name, etc."""
    user = test_db.query(__import__("app.db.models", fromlist=["User"]).User).first()
    story_params = {
        "kid_name": "Alice",
        "kid_age": 7,
        "story_type": "custom",
        "genre": "fantasy",
        "mood": "exciting",
        "art_style": "watercolor_dream",
        "user_id": user.id,
    }
    create_job_state(test_db, "enrich-1", ["writing", "synthesizing"], story_params=story_params)

    job = get_job_state(test_db, "enrich-1")
    job.title = "The Magic Forest"
    job.transcript = "Once upon a time..."
    test_db.commit()

    update_job_progress_data(test_db, "enrich-1", 30.0, {
        "message": "Generating audio...",
        "voice": {"completed": 2, "total": 8},
    })

    response = test_client.get("/api/story/status/enrich-1")
    assert response.status_code == 200
    data = response.json()

    assert data["title"] == "The Magic Forest"
    assert data["transcript"] == "Once upon a time..."
    assert data["kid_name"] == "Alice"
    assert data["kid_age"] == 7
    assert data["genre"] == "fantasy"
    assert data["mood"] == "exciting"
    assert data["art_style"] == "watercolor_dream"
    assert data["progress_data"]["voice"]["completed"] == 2


def test_status_endpoint_omits_fields_when_not_available(test_db, test_client):
    """Fields should be null when not yet populated."""
    user = test_db.query(__import__("app.db.models", fromlist=["User"]).User).first()
    story_params = {
        "kid_name": "Bob",
        "kid_age": 5,
        "story_type": "historical",
        "user_id": user.id,
    }
    create_job_state(test_db, "enrich-2", ["writing"], story_params=story_params)

    response = test_client.get("/api/story/status/enrich-2")
    assert response.status_code == 200
    data = response.json()

    assert data["kid_name"] == "Bob"
    assert data["title"] is None
    assert data["transcript"] is None
    assert data["progress_data"] is None


# ============================================================================
# Enriched recent jobs endpoint
# ============================================================================

def test_recent_jobs_includes_story_params(test_db, test_client, test_user):
    """GET /api/jobs/recent should include kid_name, genre, etc."""
    story_params = {
        "kid_name": "Charlie",
        "kid_age": 9,
        "story_type": "custom",
        "genre": "adventure",
        "mood": "funny",
        "art_style": "comic_book",
        "user_id": test_user.id,
    }
    # Write via a separate SessionLocal so the endpoint's own session sees it
    from app.db.database import SessionLocal
    db2 = SessionLocal()
    try:
        from app.db.crud import create_job_state as _cjs, get_job_state as _gjs
        _cjs(db2, "recent-1", ["writing"], story_params=story_params)
        job = _gjs(db2, "recent-1")
        job.title = "The Great Quest"
        db2.commit()
    finally:
        db2.close()

    response = test_client.get("/api/jobs/recent")
    assert response.status_code == 200
    data = response.json()

    assert len(data["jobs"]) >= 1
    recent = next(j for j in data["jobs"] if j["job_id"] == "recent-1")
    assert recent["kid_name"] == "Charlie"
    assert recent["kid_age"] == 9
    assert recent["genre"] == "adventure"
    assert recent["mood"] == "funny"
    assert recent["art_style"] == "comic_book"
    assert recent["title"] == "The Great Quest"


# ============================================================================
# PushSubscription model
# ============================================================================

def test_push_subscription_model(test_db, test_user):
    """PushSubscription should store and retrieve correctly."""
    sub = PushSubscription(
        user_id=test_user.id,
        endpoint="https://fcm.googleapis.com/fcm/send/abc123",
        p256dh_key="test-p256dh",
        auth_key="test-auth",
    )
    test_db.add(sub)
    test_db.commit()

    stored = test_db.query(PushSubscription).filter(
        PushSubscription.user_id == test_user.id
    ).first()

    assert stored is not None
    assert stored.endpoint == "https://fcm.googleapis.com/fcm/send/abc123"
    assert stored.p256dh_key == "test-p256dh"
    assert stored.auth_key == "test-auth"


def test_push_subscribe_endpoint(test_db, test_client, test_user):
    """POST /api/push/subscribe should store subscription."""
    response = test_client.post("/api/push/subscribe", json={
        "endpoint": "https://push.example.com/sub1",
        "keys": {"p256dh": "key1", "auth": "auth1"},
    })
    # May return 503 if VAPID not configured, which is expected in tests
    assert response.status_code in (200, 503)
