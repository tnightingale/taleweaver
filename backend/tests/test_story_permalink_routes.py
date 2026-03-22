"""
Tests for Permalink API Routes
Testing /api/permalink/{short_id} endpoints (backend API)

Note: /s/{short_id} routes are handled by frontend SPA in production (Caddy routing).
Backend provides /api/permalink/{short_id} which frontend fetches data from.
"""
import pytest
from pathlib import Path

from app.db.crud import save_story


def test_get_story_by_short_id_returns_metadata(test_db, test_client):
    """GET /api/permalink/{short_id} returns story metadata"""
    # Create a story in isolated test database
    story = save_story(
        db=test_db,
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
    
    response = test_client.get(f"/api/permalink/{short_id}")
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
    assert data["permalink"] == f"/s/{short_id}"  # Frontend permalink format
    assert data["audio_url"] == f"/api/permalink/{short_id}/audio"  # Backend API format


def test_get_story_audio_by_short_id(test_db, test_client):
    """GET /api/permalink/{short_id}/audio streams audio file"""
    # Create story in isolated test database
    story = save_story(
        db=test_db,
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
    
    response = test_client.get(f"/api/permalink/{short_id}/audio")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert b"test audio content for permalink" in response.content


def test_short_id_not_found_returns_404(test_client):
    """Non-existent short ID returns 404"""
    response = test_client.get("/api/permalink/notfound")
    assert response.status_code == 404


def test_short_id_audio_not_found_returns_404(test_client):
    """Non-existent short ID for audio returns 404"""
    response = test_client.get("/api/permalink/notfound/audio")
    assert response.status_code == 404


def test_audio_streaming_has_correct_headers(test_db, test_client):
    """Audio response has proper Content-Type and Content-Disposition"""
    # Create story in isolated test database
    story = save_story(
        db=test_db,
        story_id="permalink-test-headers-check",
        title="Header Test Story",
        kid_name="Test",
        kid_age=6,
        story_type="custom",
        transcript="Test",
        duration_seconds=120,
        audio_bytes=b"audio data",
    )
    short_id = story.short_id
    
    response = test_client.get(f"/api/permalink/{short_id}/audio")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    # FileResponse uses "attachment" by default
    assert "attachment" in response.headers["content-disposition"]
    assert "Header%20Test%20Story.mp3" in response.headers["content-disposition"]
    assert "content-length" in response.headers
    assert "accept-ranges" in response.headers
