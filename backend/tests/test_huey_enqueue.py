"""
Tests that story creation endpoints enqueue huey tasks instead of
using asyncio.create_task.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_custom_story_enqueues_huey_task(test_db, test_client):
    """POST /api/story/custom should enqueue a huey task, not asyncio.create_task."""
    with patch("app.jobs.tasks.generate_story_task") as mock_task:
        response = test_client.post("/api/story/custom", json={
            "kid": {"name": "Arjun", "age": 7},
            "genre": "adventure",
            "description": "A pirate story",
            "mood": "exciting",
            "length": "medium",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "job_id" in data

        # Must have called the huey task (not asyncio.create_task)
        mock_task.assert_called_once()
        call_args = mock_task.call_args
        job_id = call_args[0][0]  # first positional arg
        story_params = call_args[0][1]  # second positional arg

        assert job_id == data["job_id"]
        assert story_params["kid_name"] == "Arjun"
        assert story_params["kid_age"] == 7
        assert story_params["genre"] == "adventure"
        assert story_params["mood"] == "exciting"


def test_historical_story_enqueues_huey_task(test_db, test_client):
    """POST /api/story/historical should enqueue a huey task."""
    with patch("app.jobs.tasks.generate_story_task") as mock_task:
        response = test_client.post("/api/story/historical", json={
            "kid": {"name": "Maya", "age": 9},
            "event_id": "shivaji-agra-escape",
            "mood": "exciting",
            "length": "long",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"

        mock_task.assert_called_once()
        story_params = mock_task.call_args[0][1]
        assert story_params["kid_name"] == "Maya"
        assert story_params["story_type"] == "historical"
        assert story_params["event_id"] == "shivaji-agra-escape"


def test_no_asyncio_create_task_in_routes():
    """
    story.py should not use asyncio.create_task anywhere.
    This is a code-level assertion to prevent regression.
    """
    import inspect
    from app.routes import story

    source = inspect.getsource(story)
    assert "asyncio.create_task" not in source, (
        "story.py still uses asyncio.create_task — "
        "all background work must go through huey tasks"
    )
