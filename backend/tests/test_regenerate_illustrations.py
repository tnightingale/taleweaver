"""
Tests for illustration regeneration endpoint and CRUD
"""
import pytest
from unittest.mock import patch, MagicMock

from app.db.crud import save_story, get_story_by_short_id


def test_regenerate_endpoint_returns_job(test_db, test_client):
    """POST /api/stories/{short_id}/regenerate-illustrations creates a regen job"""
    story = save_story(
        db=test_db,
        story_id="regen-test-1",
        title="Test Story",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img.png", "illustration_prompt": "Prompt 0",
                 "generation_metadata": {"succeeded": True}},
                {"beat_index": 1, "image_url": None, "illustration_prompt": "Prompt 1",
                 "generation_metadata": {"succeeded": False, "error": "timeout"}},
            ],
            "art_style_prompt": "watercolor",
        },
    )

    with patch("app.jobs.tasks.regenerate_illustrations_task") as mock_task:
        response = test_client.post(f"/api/stories/{story.short_id}/regenerate-illustrations")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["failed_count"] == 1
    assert data["total_scenes"] == 2
    assert "job_id" in data
    mock_task.assert_called_once()


def test_regenerate_endpoint_all_present(test_db, test_client):
    """Should return ok message when all illustrations already present"""
    story = save_story(
        db=test_db,
        story_id="regen-all-ok",
        title="All Good",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img0.png",
                 "generation_metadata": {"succeeded": True}},
                {"beat_index": 1, "image_url": "/img1.png",
                 "generation_metadata": {"succeeded": True}},
            ],
        },
    )

    response = test_client.post(f"/api/stories/{story.short_id}/regenerate-illustrations")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "already present" in data["message"]


def test_regenerate_endpoint_no_art_style(test_db, test_client):
    """Should return 400 when story has no art style"""
    story = save_story(
        db=test_db,
        story_id="regen-no-style",
        title="No Style",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
    )

    response = test_client.post(f"/api/stories/{story.short_id}/regenerate-illustrations")
    assert response.status_code == 400
    assert "art style" in response.json()["detail"].lower()


def test_regenerate_endpoint_not_found(test_client):
    """Should return 404 for non-existent story"""
    response = test_client.post("/api/stories/notfound/regenerate-illustrations")
    assert response.status_code == 404


def test_regenerate_endpoint_no_scene_data(test_db, test_client):
    """Should return 400 when story has no scene data"""
    story = save_story(
        db=test_db,
        story_id="regen-no-scenes",
        title="No Scenes",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
    )

    response = test_client.post(f"/api/stories/{story.short_id}/regenerate-illustrations")
    assert response.status_code == 400
    assert "scene data" in response.json()["detail"].lower()
