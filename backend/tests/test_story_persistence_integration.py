"""
TDD Tests for Story Persistence Integration with Pipeline
RED Phase: These tests should FAIL initially
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import tempfile
from pathlib import Path
import shutil

from app.main import app
from app.db.database import SessionLocal, init_db
from app.db.crud import get_story_by_id, get_story_by_short_id

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db_env(tmp_path):
    """Set up test database environment"""
    import app.db.database as db_module
    import app.config as config_module
    
    # Store originals
    original_db_url = db_module.SQLALCHEMY_DATABASE_URL
    original_storage = config_module.settings.storage_path
    
    # Override paths
    test_db_path = tmp_path / "test.db"
    db_module.SQLALCHEMY_DATABASE_URL = f"sqlite:///{test_db_path}"
    config_module.settings.storage_path = tmp_path
    
    # Recreate engine
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    db_module.engine = create_engine(
        db_module.SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_module.engine)
    
    # Initialize tables
    init_db()
    
    yield tmp_path
    
    # Restore
    db_module.SQLALCHEMY_DATABASE_URL = original_db_url
    config_module.settings.storage_path = original_storage


def test_completed_story_is_saved_to_database(test_db_env):
    """After pipeline completes, story is persisted to database"""
    # Mock the pipeline to complete immediately
    with patch("app.routes.story.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
        # Simulate completed job
        async def mock_run(job_id, state):
            from app.routes.story import jobs
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["title"] = "Test Story"
            jobs[job_id]["duration_seconds"] = 180
            jobs[job_id]["final_audio"] = b"fake audio"
            jobs[job_id]["transcript"] = "Test transcript"
            jobs[job_id]["short_id"] = "abc123de"  # Should be set by persistence
        
        mock_pipeline.side_effect = mock_run
        
        # Create story
        response = client.post("/api/story/custom", json={
            "kid": {"name": "Test Kid", "age": 7},
            "genre": "fantasy",
            "description": "A test story"
        })
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Verify story was saved to database
        db = SessionLocal()
        try:
            story = get_story_by_id(db, job_id)
            assert story is not None, "Story should be saved to database"
            assert story.title == "Test Story"
            assert story.short_id is not None
        finally:
            db.close()


def test_completed_story_has_audio_file(test_db_env):
    """Saved story has audio file on filesystem"""
    with patch("app.routes.story.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
        async def mock_run(job_id, state):
            from app.routes.story import jobs
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["title"] = "Audio Test"
            jobs[job_id]["duration_seconds"] = 100
            jobs[job_id]["final_audio"] = b"test audio bytes"
            jobs[job_id]["transcript"] = "Audio test"
            jobs[job_id]["short_id"] = "xyz789ab"
        
        mock_pipeline.side_effect = mock_run
        
        response = client.post("/api/story/custom", json={
            "kid": {"name": "Audio Kid", "age": 5},
            "genre": "adventure",
            "description": "Test"
        })
        job_id = response.json()["job_id"]
        
        # Check audio file exists
        db = SessionLocal()
        try:
            story = get_story_by_id(db, job_id)
            assert story is not None
            audio_path = Path(story.audio_path)
            assert audio_path.exists(), "Audio file should exist on filesystem"
            assert audio_path.read_bytes() == b"test audio bytes"
        finally:
            db.close()


def test_job_status_includes_short_id(test_db_env):
    """Job status response includes short_id and permalink fields"""
    with patch("app.routes.story.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
        async def mock_run(job_id, state):
            from app.routes.story import jobs
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["title"] = "Permalink Test"
            jobs[job_id]["duration_seconds"] = 150
            jobs[job_id]["final_audio"] = b"audio"
            jobs[job_id]["transcript"] = "Transcript"
            jobs[job_id]["short_id"] = "perm123x"
        
        mock_pipeline.side_effect = mock_run
        
        response = client.post("/api/story/custom", json={
            "kid": {"name": "Link Kid", "age": 8},
            "genre": "space",
            "description": "Test"
        })
        job_id = response.json()["job_id"]
        
        # Get status
        status_response = client.get(f"/api/story/status/{job_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        
        assert "short_id" in data, "Response should include short_id"
        assert "permalink" in data, "Response should include permalink"
        assert data["short_id"] == "perm123x"
        assert data["permalink"] == "/s/perm123x"


def test_old_job_audio_endpoint_still_works(test_db_env):
    """Backward compatibility: /api/story/audio/{job_id} still works"""
    with patch("app.routes.story.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
        async def mock_run(job_id, state):
            from app.routes.story import jobs
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["title"] = "Compat Test"
            jobs[job_id]["duration_seconds"] = 90
            jobs[job_id]["final_audio"] = b"compat audio"
            jobs[job_id]["transcript"] = "Test"
            jobs[job_id]["short_id"] = "compat12"
        
        mock_pipeline.side_effect = mock_run
        
        response = client.post("/api/story/custom", json={
            "kid": {"name": "Compat Kid", "age": 6},
            "genre": "funny",
            "description": "Test"
        })
        job_id = response.json()["job_id"]
        
        # Old endpoint should still work
        audio_response = client.get(f"/api/story/audio/{job_id}")
        assert audio_response.status_code == 200
        assert audio_response.headers["content-type"] == "audio/mpeg"
