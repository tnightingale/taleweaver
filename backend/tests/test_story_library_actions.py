"""
TDD Tests for Story Library Actions (Delete & Update)
RED Phase: These tests should FAIL initially
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.db.database import SessionLocal, init_db
from app.db.crud import save_story, get_story_by_short_id, delete_story, update_story_title

client = TestClient(app)

# Initialize database for tests
init_db()


def test_delete_story_removes_database_record():
    """Deleting a story removes it from database"""
    db = SessionLocal()
    try:
        story = save_story(
            db=db,
            story_id="delete-test-db",
            title="To Delete",
            kid_name="Test",
            kid_age=6,
            story_type="custom",
            transcript="...",
            duration_seconds=100,
            audio_bytes=b"audio",
        )
        short_id = story.short_id
    finally:
        db.close()
    
    # Delete the story
    db = SessionLocal()
    try:
        result = delete_story(db, short_id)
        assert result == True, "delete_story should return True on success"
    finally:
        db.close()
    
    # Verify it's gone
    db = SessionLocal()
    try:
        deleted = get_story_by_short_id(db, short_id)
        assert deleted is None, "Story should be deleted from database"
    finally:
        db.close()


def test_delete_story_removes_audio_file():
    """Deleting a story removes the audio file from filesystem"""
    db = SessionLocal()
    try:
        story = save_story(
            db=db,
            story_id="delete-test-file",
            title="File Delete Test",
            kid_name="Test",
            kid_age=6,
            story_type="custom",
            transcript="...",
            duration_seconds=100,
            audio_bytes=b"test audio to delete",
        )
        short_id = story.short_id
        audio_path = Path(story.audio_path)
        assert audio_path.exists(), "Audio file should exist before delete"
    finally:
        db.close()
    
    # Delete
    db = SessionLocal()
    try:
        delete_story(db, short_id)
    finally:
        db.close()
    
    # Verify audio file is gone
    assert not audio_path.exists(), "Audio file should be deleted"


def test_delete_story_not_found_returns_false():
    """Deleting non-existent story returns False"""
    db = SessionLocal()
    try:
        result = delete_story(db, "notfound")
        assert result == False, "Should return False for non-existent story"
    finally:
        db.close()


def test_delete_story_api_endpoint():
    """DELETE /api/stories/{short_id} deletes story"""
    # Create story
    db = SessionLocal()
    try:
        story = save_story(
            db=db,
            story_id="api-delete-test",
            title="API Delete",
            kid_name="Test",
            kid_age=7,
            story_type="custom",
            transcript="...",
            duration_seconds=100,
            audio_bytes=b"audio",
        )
        short_id = story.short_id
    finally:
        db.close()
    
    # Delete via API
    response = client.delete(f"/api/stories/{short_id}")
    assert response.status_code == 204, "Should return 204 No Content"
    
    # Verify it's gone
    db = SessionLocal()
    try:
        deleted = get_story_by_short_id(db, short_id)
        assert deleted is None
    finally:
        db.close()


def test_delete_story_api_not_found():
    """DELETE /api/stories/{short_id} returns 404 for non-existent story"""
    response = client.delete("/api/stories/notfound")
    assert response.status_code == 404


def test_update_story_title():
    """Updating story title changes it in database"""
    db = SessionLocal()
    try:
        story = save_story(
            db=db,
            story_id="update-test",
            title="Original Title",
            kid_name="Test",
            kid_age=6,
            story_type="custom",
            transcript="...",
            duration_seconds=100,
            audio_bytes=b"audio",
        )
        short_id = story.short_id
    finally:
        db.close()
    
    # Update title
    db = SessionLocal()
    try:
        updated = update_story_title(db, short_id, "New Title")
        assert updated is not None
        assert updated.title == "New Title"
    finally:
        db.close()
    
    # Verify it persisted
    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        assert story.title == "New Title"
    finally:
        db.close()


def test_update_story_title_not_found():
    """Updating non-existent story returns None"""
    db = SessionLocal()
    try:
        result = update_story_title(db, "notfound", "New Title")
        assert result is None
    finally:
        db.close()


def test_update_story_title_api_endpoint():
    """PATCH /api/stories/{short_id} updates title"""
    # Create story
    db = SessionLocal()
    try:
        story = save_story(
            db=db,
            story_id="api-update-test",
            title="Old Title",
            kid_name="Test",
            kid_age=7,
            story_type="custom",
            transcript="...",
            duration_seconds=100,
            audio_bytes=b"audio",
        )
        short_id = story.short_id
    finally:
        db.close()
    
    # Update via API
    response = client.patch(f"/api/stories/{short_id}", json={"title": "Updated Title"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["short_id"] == short_id
    
    # Verify in database
    db = SessionLocal()
    try:
        story = get_story_by_short_id(db, short_id)
        assert story.title == "Updated Title"
    finally:
        db.close()


def test_update_story_title_api_not_found():
    """PATCH /api/stories/{short_id} returns 404 for non-existent story"""
    response = client.patch("/api/stories/notfound", json={"title": "New"})
    assert response.status_code == 404


def test_update_story_title_api_empty_title():
    """PATCH /api/stories/{short_id} rejects empty title"""
    db = SessionLocal()
    try:
        story = save_story(
            db=db,
            story_id="empty-title-test",
            title="Valid Title",
            kid_name="Test",
            kid_age=6,
            story_type="custom",
            transcript="...",
            duration_seconds=100,
            audio_bytes=b"audio",
        )
        short_id = story.short_id
    finally:
        db.close()
    
    # Try to update with empty title
    response = client.patch(f"/api/stories/{short_id}", json={"title": ""})
    assert response.status_code == 422, "Should reject empty title with validation error"
