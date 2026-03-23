"""
Tests that the retry endpoint actually re-enqueues via huey.
"""
import json
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from app.db.crud import create_job_state, get_job_state


def test_retry_enqueues_huey_task(test_db, test_client):
    """
    POST /api/story/retry/{job_id} should re-enqueue a huey task
    when the job is resumable.
    """
    # Create a failed, resumable job with stored params
    job = create_job_state(test_db, "retry-job-1", ["writing", "synthesizing"])
    job.status = "failed"
    job.resumable = True
    job.error_message = "Quota exceeded"
    job.story_params_json = json.dumps({
        "kid_name": "Arjun",
        "kid_age": 7,
        "kid_details": "",
        "story_type": "custom",
        "genre": "adventure",
        "description": "A pirate story",
        "event_id": None,
        "event_data": None,
        "mood": "exciting",
        "length": "medium",
        "art_style": None,
        "custom_art_style_prompt": None,
    })
    test_db.commit()

    with patch("app.jobs.tasks.generate_story_task") as mock_task:
        response = test_client.post("/api/story/retry/retry-job-1")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resuming"

        # Must have re-enqueued via huey
        mock_task.assert_called_once()
        call_args = mock_task.call_args[0]
        assert call_args[0] == "retry-job-1"  # job_id
        assert call_args[1]["kid_name"] == "Arjun"  # story_params


def test_retry_without_stored_params_fails_gracefully(test_db, test_client):
    """
    If a job doesn't have stored params (legacy job), retry should
    return an appropriate error.
    """
    job = create_job_state(test_db, "legacy-job-1", ["writing"])
    job.status = "failed"
    job.resumable = True
    job.story_params_json = None
    test_db.commit()

    response = test_client.post("/api/story/retry/legacy-job-1")
    assert response.status_code == 400
    assert "cannot be retried" in response.json()["detail"].lower()


def test_custom_story_stores_params_in_job(test_db, test_client):
    """
    POST /api/story/custom should store story_params_json in the job
    so retry can re-enqueue later.
    """
    with patch("app.jobs.tasks.generate_story_task"):
        response = test_client.post("/api/story/custom", json={
            "kid": {"name": "Test", "age": 5},
            "genre": "fantasy",
            "description": "A cat story",
        })

    job_id = response.json()["job_id"]
    job = get_job_state(test_db, job_id)
    assert job.story_params_json is not None
    params = json.loads(job.story_params_json)
    assert params["kid_name"] == "Test"
    assert params["genre"] == "fantasy"
