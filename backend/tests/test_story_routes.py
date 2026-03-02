import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_custom_story_returns_job():
    with patch("app.routes.story.run_pipeline", new_callable=AsyncMock):
        response = client.post("/api/story/custom", json={
            "kid": {"name": "Arjun", "age": 7},
            "genre": "fantasy",
            "description": "A magical adventure"
        })
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["current_stage"] == "writing"


def test_create_historical_story_returns_job():
    with patch("app.routes.story.run_pipeline", new_callable=AsyncMock):
        response = client.post("/api/story/historical", json={
            "kid": {"name": "Arjun", "age": 7},
            "event_id": "shivaji-agra-escape"
        })
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data


def test_historical_story_invalid_event():
    response = client.post("/api/story/historical", json={
        "kid": {"name": "Arjun", "age": 7},
        "event_id": "nonexistent-event"
    })
    assert response.status_code == 404


def test_get_job_status_not_found():
    response = client.get("/api/story/status/nonexistent-id")
    assert response.status_code == 404


def test_get_audio_not_found():
    response = client.get("/api/story/audio/nonexistent-id")
    assert response.status_code == 404
