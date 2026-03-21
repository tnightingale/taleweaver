"""
TDD Tests for Permalink API Routes
RED Phase: These tests should FAIL initially
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.db.database import SessionLocal
from app.db.crud import save_story

client = TestClient(app)


def test_get_story_by_short_id_returns_metadata():
    """GET /s/{short_id} returns story metadata"""
    # Create a story for testing
    db = SessionLocal()
    try:
        story = save_story(
            db=db,
            story_id="permalink-test-meta",
            title="Permalink Test Story",
            kid_name="Arjun",
            kid_age=7,
            story_type="custom",
            genre="fantasy",
            mood="exciting",
            length="medium",
            transcript="Once upon a time in a magical land...",
            duration_seconds=180,
            audio_bytes=b"test audio content for permalink",
        )
        short_id = story.short_id
    finally:
        db.close()
    
    response = client.get(f"/s/{short_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == "permalink-test-meta"
    assert data["short_id"] == short_id
    assert data["title"] == "Permalink Test Story"
    assert data["kid_name"] == "Arjun"
    assert data["kid_age"] == 7
    assert data["story_type"] == "custom"
    assert data["genre"] == "fantasy"
    assert data["transcript"] == "Once upon a time in a magical land..."
    assert data["duration_seconds"] == 180
    assert data["permalink"] == f"/s/{short_id}"
    assert data["audio_url"] == f"/s/{short_id}/audio"


def test_get_story_audio_by_short_id():
    """GET /s/{short_id}/audio streams audio file"""
    # Create story
    db = SessionLocal()
    try:
        story = save_story(
            db=db,
            story_id="permalink-test-audio-stream",
            title="Audio Test",
            kid_name="Test",
            kid_age=5,
            story_type="custom",
            transcript="Test",
            duration_seconds=100,
            audio_bytes=b"test audio content for permalink",
        )
        short_id = story.short_id
    finally:
        db.close()
    
    response = client.get(f"/s/{short_id}/audio")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert b"test audio content for permalink" in response.content


def test_short_id_not_found_returns_404():
    """Non-existent short ID returns 404"""
    response = client.get("/s/notfound")
    assert response.status_code == 404


def test_short_id_audio_not_found_returns_404():
    """Non-existent short ID for audio returns 404"""
    response = client.get("/s/notfound/audio")
    assert response.status_code == 404


def test_audio_streaming_has_correct_headers(saved_story):
    """Audio response has proper Content-Type and Content-Disposition"""
    response = client.get(f"/s/{saved_story.short_id}/audio")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert "inline" in response.headers["content-disposition"]
    assert "Permalink Test Story.mp3" in response.headers["content-disposition"]
    assert "content-length" in response.headers
    assert "accept-ranges" in response.headers
