"""
Tests for crash recovery of orphaned jobs.

When the server crashes or restarts, any jobs stuck in "processing" status
are orphaned — their asyncio tasks are gone, but the DB record still says
"processing". On startup, these should be detected and marked as failed.
"""
import pytest
from datetime import datetime, timedelta

from app.db.crud import create_job_state, get_job_state


def test_recover_orphaned_jobs_marks_stale_processing_as_failed(test_db):
    """
    Jobs stuck in "processing" for too long should be marked as failed
    on startup recovery.
    """
    from app.db.crud import recover_orphaned_jobs

    # Create a job that's been "processing" for 10 minutes (clearly orphaned)
    job = create_job_state(test_db, "orphaned-job-1", ["writing", "synthesizing"])
    job.created_at = datetime.utcnow() - timedelta(minutes=10)
    job.updated_at = datetime.utcnow() - timedelta(minutes=10)
    test_db.commit()

    recovered = recover_orphaned_jobs(test_db, stale_minutes=5)

    assert recovered == 1
    refreshed = get_job_state(test_db, "orphaned-job-1")
    assert refreshed.status == "failed"
    assert "interrupted" in refreshed.error_message.lower() or "crash" in refreshed.error_message.lower()


def test_recover_orphaned_jobs_ignores_recent_processing(test_db):
    """
    Jobs that were recently updated should NOT be marked as failed —
    they may still be legitimately running.
    """
    from app.db.crud import recover_orphaned_jobs

    # Create a job that was updated 1 minute ago (still active)
    job = create_job_state(test_db, "active-job-1", ["writing", "synthesizing"])
    job.updated_at = datetime.utcnow() - timedelta(minutes=1)
    test_db.commit()

    recovered = recover_orphaned_jobs(test_db, stale_minutes=5)

    assert recovered == 0
    refreshed = get_job_state(test_db, "active-job-1")
    assert refreshed.status == "processing"


def test_recover_orphaned_jobs_ignores_completed_jobs(test_db):
    """Completed/failed jobs should not be touched."""
    from app.db.crud import recover_orphaned_jobs

    job = create_job_state(test_db, "done-job-1", ["writing"])
    job.status = "complete"
    job.updated_at = datetime.utcnow() - timedelta(hours=1)
    test_db.commit()

    recovered = recover_orphaned_jobs(test_db, stale_minutes=5)
    assert recovered == 0


def test_recover_multiple_orphaned_jobs(test_db):
    """Should recover all stale processing jobs at once."""
    from app.db.crud import recover_orphaned_jobs

    for i in range(3):
        job = create_job_state(test_db, f"orphan-{i}", ["writing"])
        job.updated_at = datetime.utcnow() - timedelta(minutes=15)
    test_db.commit()

    recovered = recover_orphaned_jobs(test_db, stale_minutes=5)
    assert recovered == 3

    for i in range(3):
        j = get_job_state(test_db, f"orphan-{i}")
        assert j.status == "failed"


def test_startup_calls_recovery(test_db):
    """
    The app startup event should call recover_orphaned_jobs so that
    stale jobs are cleaned up whenever the server restarts.
    """
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.main import app

    with patch("app.db.crud.recover_orphaned_jobs", return_value=0) as mock_recover:
        # Trigger startup by creating a test client
        # (TestClient triggers startup/shutdown events)
        with TestClient(app):
            pass

        mock_recover.assert_called_once()
