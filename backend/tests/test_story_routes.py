import pytest
from unittest.mock import patch, AsyncMock


def test_create_custom_story_returns_job(test_db, test_client):
    with patch("app.routes.story.run_pipeline", new_callable=AsyncMock):
        response = test_client.post("/api/story/custom", json={
            "kid": {"name": "Arjun", "age": 7},
            "genre": "fantasy",
            "description": "A magical adventure"
        })
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["current_stage"] == "writing"


def test_create_historical_story_returns_job(test_db, test_client):
    with patch("app.routes.story.run_pipeline", new_callable=AsyncMock):
        response = test_client.post("/api/story/historical", json={
            "kid": {"name": "Arjun", "age": 7},
            "event_id": "shivaji-agra-escape"
        })
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


def test_historical_story_invalid_event(test_client):
    response = test_client.post("/api/story/historical", json={
        "kid": {"name": "Arjun", "age": 7},
        "event_id": "nonexistent-event"
    })
    assert response.status_code == 404


def test_get_job_status_not_found(test_client):
    response = test_client.get("/api/story/status/nonexistent-id")
    assert response.status_code == 404


def test_get_audio_not_found(test_client):
    response = test_client.get("/api/story/audio/nonexistent-id")
    assert response.status_code == 404


def test_get_audio_returns_correct_headers(test_db, test_client):
    from app.db.crud import save_story
    
    # Create a story with audio file
    job_id = "test-audio-headers"
    save_story(
        db=test_db,
        story_id=job_id,
        title="Audio Test",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="Test",
        duration_seconds=100,
        audio_bytes=b"\xff\xfb\x90\x00" * 100,  # fake MP3 bytes
    )
    
    response = test_client.get(f"/api/story/audio/{job_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert "inline" in response.headers["content-disposition"]


def test_get_audio_download_mode(test_db, test_client):
    from app.db.crud import save_story
    
    # Create a story with audio file
    job_id = "test-audio-download"
    save_story(
        db=test_db,
        story_id=job_id,
        title="Download Test",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="Test",
        duration_seconds=100,
        audio_bytes=b"\xff\xfb\x90\x00" * 200,
    )
    
    response = test_client.get(f"/api/story/audio/{job_id}?download=true")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
