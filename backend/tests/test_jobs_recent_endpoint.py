"""
Tests for GET /api/jobs/recent endpoint (TDD RED Phase)
Testing recent jobs listing for navigation persistence
"""
import pytest
from datetime import datetime, timedelta

from app.db.crud import create_job_state


def test_recent_jobs_endpoint_returns_jobs_from_last_24h(test_db, test_client):
    """Should return jobs created in last 24 hours"""
    # Create jobs with different ages
    # Recent job (1 hour ago)
    job1 = create_job_state(test_db, "recent-1", ["writing"])
    job1.created_at = datetime.utcnow() - timedelta(hours=1)
    job1.title = "Recent Story 1"
    job1.status = "processing"
    test_db.commit()
    
    # Old job (25 hours ago) - should NOT be returned
    job2 = create_job_state(test_db, "old-1", ["writing"])
    job2.created_at = datetime.utcnow() - timedelta(hours=25)
    job2.title = "Old Story"
    test_db.commit()
    
    response = test_client.get("/api/jobs/recent")
    
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    
    # Should only have recent job
    job_ids = [j["job_id"] for j in data["jobs"]]
    assert "recent-1" in job_ids
    assert "old-1" not in job_ids


def test_recent_jobs_endpoint_includes_job_details(test_db, test_client):
    """Should include status, progress, title, and stage for each job"""
    job = create_job_state(test_db, "details-test", ["writing", "synthesizing"])
    job.status = "processing"
    job.current_stage = "synthesizing"
    job.progress = 45.5
    job.title = "Test Story Title"
    test_db.commit()
    
    response = test_client.get("/api/jobs/recent")
    
    assert response.status_code == 200
    data = response.json()
    
    jobs = data["jobs"]
    assert len(jobs) > 0
    
    # Find our test job
    test_job = next(j for j in jobs if j["job_id"] == "details-test")
    
    assert test_job["status"] == "processing"
    assert test_job["current_stage"] == "synthesizing"
    assert test_job["progress"] == 45.5
    assert test_job["title"] == "Test Story Title"
    assert "created_at" in test_job


def test_recent_jobs_endpoint_sorted_by_created_desc(test_db, test_client):
    """Should return jobs sorted by created_at descending (newest first)"""
    # Create 3 jobs at different times
    job1 = create_job_state(test_db, "sort-1", ["writing"])
    job1.created_at = datetime.utcnow() - timedelta(hours=5)
    job1.title = "Oldest"
    test_db.commit()
    
    job2 = create_job_state(test_db, "sort-2", ["writing"])
    job2.created_at = datetime.utcnow() - timedelta(hours=2)
    job2.title = "Middle"
    test_db.commit()
    
    job3 = create_job_state(test_db, "sort-3", ["writing"])
    job3.created_at = datetime.utcnow() - timedelta(minutes=10)
    job3.title = "Newest"
    test_db.commit()
    
    response = test_client.get("/api/jobs/recent")
    
    data = response.json()
    jobs = data["jobs"]
    
    # Should be sorted newest first
    assert jobs[0]["title"] == "Newest"
    assert jobs[1]["title"] == "Middle"
    assert jobs[2]["title"] == "Oldest"


def test_recent_jobs_endpoint_limits_to_20(test_db, test_client):
    """Should limit results to 20 most recent jobs"""
    # Create 25 jobs
    for i in range(25):
        job = create_job_state(test_db, f"limit-{i}", ["writing"])
        job.title = f"Story {i}"
        job.created_at = datetime.utcnow() - timedelta(hours=i)
        test_db.commit()
    
    response = test_client.get("/api/jobs/recent")
    
    data = response.json()
    assert len(data["jobs"]) <= 20


def test_recent_jobs_endpoint_includes_in_progress_and_complete(test_db, test_client):
    """Should include both processing and complete jobs (not just processing)"""
    job1 = create_job_state(test_db, "status-processing", ["writing"])
    job1.status = "processing"
    test_db.commit()
    
    job2 = create_job_state(test_db, "status-complete", ["writing"])
    job2.status = "complete"
    job2.title = "Completed Story"
    test_db.commit()
    
    job3 = create_job_state(test_db, "status-failed", ["writing"])
    job3.status = "failed"
    test_db.commit()
    
    response = test_client.get("/api/jobs/recent")
    
    data = response.json()
    statuses = [j["status"] for j in data["jobs"]]
    
    assert "processing" in statuses
    assert "complete" in statuses
    assert "failed" in statuses
