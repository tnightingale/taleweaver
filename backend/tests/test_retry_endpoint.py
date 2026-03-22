"""
Tests for Retry Endpoint (TDD RED Phase)
Testing job resume functionality for quota/rate limit errors
"""
import pytest
import json

from app.db.crud import create_job_state, get_job_state


def test_retry_endpoint_resumes_failed_job(test_db, test_client):
    """Should resume a failed resumable job"""
    # Create a failed job with resumable flag
    job = create_job_state(test_db, "retry-test-1", ["writing", "synthesizing"])
    job.status = "failed"
    job.resumable = True
    job.partial_data_json = json.dumps({
        "segments_completed": 5,
        "segments_total": 12,
        "checkpoint_node": "voice_synthesizer"
    })
    job.error_message = "Voice synthesis quota exceeded"
    test_db.commit()
    
    # Retry the job
    response = test_client.post(f"/api/story/retry/retry-test-1")
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "retry-test-1"
    assert data["status"] == "resuming"
    assert data["retry_count"] == 1
    
    # Verify job state updated
    test_db.expire_all()
    job = get_job_state(test_db, "retry-test-1")
    assert job.status == "processing"
    assert job.retry_count == 1
    assert job.error_message is None


def test_retry_endpoint_job_not_found(test_client):
    """Should return 404 for non-existent job"""
    response = test_client.post("/api/story/retry/nonexistent")
    assert response.status_code == 404


def test_retry_endpoint_job_not_failed(test_db, test_client):
    """Should return 400 if job is not in failed state"""
    # Create a processing job
    create_job_state(test_db, "retry-test-processing", ["writing"])
    # Leave as processing
    
    response = test_client.post("/api/story/retry/retry-test-processing")
    assert response.status_code == 400
    assert "not in a failed state" in response.json()["detail"]


def test_retry_endpoint_job_not_resumable(test_db, test_client):
    """Should return 400 if job is not resumable"""
    # Create failed job that's NOT resumable
    job = create_job_state(test_db, "retry-test-permanent", ["writing"])
    job.status = "failed"
    job.resumable = False  # Permanent error
    job.error_message = "Invalid API key"
    test_db.commit()
    
    response = test_client.post("/api/story/retry/retry-test-permanent")
    assert response.status_code == 400
    assert "cannot be resumed" in response.json()["detail"]


def test_retry_endpoint_max_retries_exceeded(test_db, test_client):
    """Should return 400 if retry limit exceeded"""
    # Create failed job with 3 retries already
    job = create_job_state(test_db, "retry-test-max", ["writing"])
    job.status = "failed"
    job.resumable = True
    job.retry_count = 3  # Max retries
    test_db.commit()
    
    response = test_client.post("/api/story/retry/retry-test-max")
    assert response.status_code == 400
    assert "Maximum retry limit" in response.json()["detail"]


def test_job_status_includes_resumable_info(test_db, test_client):
    """JobStatusResponse should include resumable and partial progress"""
    # Create failed resumable job
    job = create_job_state(test_db, "status-test-resumable", ["writing", "synthesizing"])
    job.status = "failed"
    job.resumable = True
    job.partial_data_json = json.dumps({
        "segments_completed": 7,
        "segments_total": 12,
        "checkpoint_node": "voice_synthesizer"
    })
    job.error_message = "Quota exceeded"
    test_db.commit()
    
    response = test_client.get("/api/story/status/status-test-resumable")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["resumable"] is True
    assert data["partial_progress"] is not None
    assert data["partial_progress"]["segments_completed"] == 7
    assert data["partial_progress"]["segments_total"] == 12
