"""
Tests for JobState Model and CRUD (TDD RED Phase)
These tests will FAIL until JobState model and CRUD functions are implemented
"""
import pytest
import json
from datetime import datetime, timedelta

from app.db.crud import (
    create_job_state,
    get_job_state, 
    update_job_stage,
    update_job_progress,
    mark_job_complete,
    mark_job_failed,
    cleanup_old_jobs,
)
from app.db.models import JobState


def test_create_job_state(test_db):
    """Should create job state in database"""
    stages = ["writing", "splitting", "synthesizing", "stitching"]
    
    job = create_job_state(test_db, "test-job-1", stages)
    
    assert job.job_id == "test-job-1"
    assert job.status == "processing"
    assert job.current_stage == "writing"
    assert json.loads(job.stages) == stages
    assert job.created_at is not None


def test_get_job_state(test_db):
    """Should retrieve job state from database"""
    # Create job
    create_job_state(test_db, "test-job-2", ["writing"])
    
    # Retrieve it
    job = get_job_state(test_db, "test-job-2")
    
    assert job is not None
    assert job.job_id == "test-job-2"
    assert job.status == "processing"


def test_get_job_state_not_found(test_db):
    """Should return None for non-existent job"""
    job = get_job_state(test_db, "nonexistent")
    assert job is None


def test_update_job_stage(test_db):
    """Should update job stage and progress"""
    create_job_state(test_db, "test-job-3", ["writing", "splitting"])
    
    # Update stage
    update_job_stage(test_db, "test-job-3", "splitting", progress=50.0)
    
    # Verify
    job = get_job_state(test_db, "test-job-3")
    assert job.current_stage == "splitting"
    assert job.progress == 50.0
    assert job.updated_at is not None


def test_update_job_progress(test_db):
    """Should update job progress and detail message"""
    create_job_state(test_db, "test-job-4", ["writing"])
    
    # Update progress
    update_job_progress(test_db, "test-job-4", 75.0, "Generating illustration 6 of 8")
    
    # Verify
    job = get_job_state(test_db, "test-job-4")
    assert job.progress == 75.0
    assert job.progress_detail == "Generating illustration 6 of 8"


def test_mark_job_complete(test_db):
    """Should mark job as complete with all metadata"""
    create_job_state(test_db, "test-job-5", ["writing"])
    
    scenes = [{"beat_index": 0, "beat_name": "Once upon a time"}]
    
    # Mark complete
    mark_job_complete(
        test_db,
        "test-job-5",
        title="Test Story",
        duration_seconds=120,
        transcript="Story text",
        short_id="abc123",
        art_style="watercolor_dream",
        scenes=scenes
    )
    
    # Verify
    job = get_job_state(test_db, "test-job-5")
    assert job.status == "complete"
    assert job.title == "Test Story"
    assert job.duration_seconds == 120
    assert job.transcript == "Story text"
    assert job.short_id == "abc123"
    assert job.art_style == "watercolor_dream"
    assert json.loads(job.scenes_json) == scenes


def test_mark_job_failed(test_db):
    """Should mark job as failed with error message"""
    create_job_state(test_db, "test-job-6", ["writing"])
    
    # Mark failed
    mark_job_failed(test_db, "test-job-6", "API quota exceeded")
    
    # Verify
    job = get_job_state(test_db, "test-job-6")
    assert job.status == "failed"
    assert job.error_message == "API quota exceeded"


def test_cleanup_old_jobs(test_db):
    """Should cleanup completed/failed jobs older than threshold"""
    # Create old completed job (25 hours ago)
    old_job = create_job_state(test_db, "old-job", ["writing"])
    old_job.status = "complete"
    old_job.created_at = datetime.utcnow() - timedelta(hours=25)
    test_db.commit()
    
    # Create recent completed job (1 hour ago)
    recent_job = create_job_state(test_db, "recent-job", ["writing"])
    recent_job.status = "complete"
    recent_job.created_at = datetime.utcnow() - timedelta(hours=1)
    test_db.commit()
    
    # Create active job
    active_job = create_job_state(test_db, "active-job", ["writing"])
    # Leave as processing
    
    # Cleanup jobs older than 24 hours
    deleted_count = cleanup_old_jobs(test_db, max_age_hours=24)
    
    # Verify
    assert deleted_count == 1
    assert get_job_state(test_db, "old-job") is None
    assert get_job_state(test_db, "recent-job") is not None
    assert get_job_state(test_db, "active-job") is not None


def test_job_state_shared_between_sessions(test_db):
    """Job state should be visible across different database sessions (simulates workers)"""
    # Session 1 (Worker 1): Create job
    create_job_state(test_db, "shared-job", ["writing", "stitching"])
    test_db.commit()
    
    # Session 2 (Worker 2): Retrieve job
    from app.db.database import SessionLocal
    db2 = SessionLocal()
    try:
        job = get_job_state(db2, "shared-job")
        assert job is not None
        assert job.job_id == "shared-job"
        assert job.status == "processing"
    finally:
        db2.close()


def test_concurrent_job_updates(test_db):
    """Concurrent updates should not cause data loss"""
    create_job_state(test_db, "concurrent-job", ["writing"])
    
    # Simulate two workers updating different fields
    update_job_stage(test_db, "concurrent-job", "splitting")
    update_job_progress(test_db, "concurrent-job", 25.0, "Processing...")
    
    # Both updates should persist
    job = get_job_state(test_db, "concurrent-job")
    assert job.current_stage == "splitting"
    assert job.progress == 25.0


def test_job_state_model_has_required_fields(test_db):
    """JobState model should have all required fields"""
    from app.db.models import JobState
    
    job = JobState(
        job_id="field-test",
        status="processing",
        current_stage="writing",
        stages=json.dumps(["writing"]),
    )
    
    # Verify all fields accessible
    assert hasattr(job, 'job_id')
    assert hasattr(job, 'status')
    assert hasattr(job, 'current_stage')
    assert hasattr(job, 'stages')
    assert hasattr(job, 'progress')
    assert hasattr(job, 'progress_detail')
    assert hasattr(job, 'title')
    assert hasattr(job, 'duration_seconds')
    assert hasattr(job, 'transcript')
    assert hasattr(job, 'art_style')
    assert hasattr(job, 'scenes_json')
    assert hasattr(job, 'short_id')
    assert hasattr(job, 'error_message')
    assert hasattr(job, 'created_at')
    assert hasattr(job, 'updated_at')
