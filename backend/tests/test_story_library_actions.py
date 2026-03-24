"""
Tests for Story Library Actions (Delete & Update)
Uses isolated test database fixtures from conftest.py
"""
import pytest
from pathlib import Path

from app.db.crud import save_story, get_story_by_short_id, delete_story, update_story_title, update_story_illustrations


def test_delete_story_removes_database_record(test_db):
    """Deleting a story removes it from database"""
    story = save_story(
        db=test_db,
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
    
    # Delete the story
    result = delete_story(test_db, short_id)
    assert result == True, "delete_story should return True on success"
    
    # Verify it's gone
    deleted = get_story_by_short_id(test_db, short_id)
    assert deleted is None, "Story should be deleted from database"


def test_delete_story_removes_audio_file(test_db):
    """Deleting a story removes the audio file from filesystem"""
    story = save_story(
        db=test_db,
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
    
    # Delete
    delete_story(test_db, short_id)
    
    # Verify audio file is gone
    assert not audio_path.exists(), "Audio file should be deleted"


def test_delete_story_not_found_returns_false(test_db):
    """Deleting non-existent story returns False"""
    result = delete_story(test_db, "notfound")
    assert result == False, "Should return False for non-existent story"


def test_delete_story_api_endpoint(test_db, test_client, test_user):
    """DELETE /api/stories/{short_id} deletes story"""
    # Create story in isolated database
    story = save_story(
        db=test_db,
        story_id="api-delete-test",
        title="API Delete",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        user_id=test_user.id,
    )
    short_id = story.short_id
    
    # Delete via API
    response = test_client.delete(f"/api/stories/{short_id}")
    assert response.status_code == 204, "Should return 204 No Content"
    
    # Verify it's gone
    deleted = get_story_by_short_id(test_db, short_id)
    assert deleted is None


def test_delete_story_api_not_found(test_client):
    """DELETE /api/stories/{short_id} returns 404 for non-existent story"""
    response = test_client.delete("/api/stories/notfound")
    assert response.status_code == 404


def test_update_story_title(test_db):
    """Updating story title changes it in database"""
    story = save_story(
        db=test_db,
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
    
    # Update title
    updated = update_story_title(test_db, short_id, "New Title")
    assert updated is not None
    assert updated.title == "New Title"
    
    # Verify it persisted
    story = get_story_by_short_id(test_db, short_id)
    assert story.title == "New Title"


def test_update_story_title_not_found(test_db):
    """Updating non-existent story returns None"""
    result = update_story_title(test_db, "notfound", "New Title")
    assert result is None


def test_update_story_title_api_endpoint(test_db, test_client, test_user):
    """PATCH /api/stories/{short_id} updates title"""
    # Create story in isolated database
    story = save_story(
        db=test_db,
        story_id="api-update-test",
        title="Old Title",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        user_id=test_user.id,
    )
    short_id = story.short_id
    
    # Update via API
    response = test_client.patch(f"/api/stories/{short_id}", json={"title": "Updated Title"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["short_id"] == short_id
    
    # Verify in database (expire and refetch to see changes from other session)
    test_db.expire_all()  # Clear session cache
    story = get_story_by_short_id(test_db, short_id)
    assert story.title == "Updated Title"


def test_update_story_title_api_not_found(test_client):
    """PATCH /api/stories/{short_id} returns 404 for non-existent story"""
    response = test_client.patch("/api/stories/notfound", json={"title": "New"})
    assert response.status_code == 404


def test_update_story_title_api_empty_title(test_db, test_client, test_user):
    """PATCH /api/stories/{short_id} rejects empty title"""
    # Create story in isolated database
    story = save_story(
        db=test_db,
        story_id="empty-title-test",
        title="Valid Title",
        kid_name="Test",
        kid_age=6,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        user_id=test_user.id,
    )
    short_id = story.short_id
    
    # Try to update with empty title
    response = test_client.patch(f"/api/stories/{short_id}", json={"title": ""})
    assert response.status_code == 422, "Should reject empty title with validation error"


# ============================================================================
# Update Story Illustrations
# ============================================================================


def test_update_story_illustrations(test_db):
    """update_story_illustrations updates scene_data and has_illustrations flag"""
    story = save_story(
        db=test_db,
        story_id="illust-update-test",
        title="Test Story",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        scene_data=None,
    )
    short_id = story.short_id
    assert story.has_illustrations is False

    new_scene_data = {
        "scenes": [
            {"beat_index": 0, "image_url": "/storage/stories/test/scene_0.png"},
            {"beat_index": 1, "image_url": None},
        ],
        "art_style_prompt": "watercolor",
    }

    updated = update_story_illustrations(test_db, short_id, new_scene_data)
    assert updated is not None
    assert updated.scene_data == new_scene_data
    assert updated.has_illustrations is True  # at least one scene has image_url


def test_update_story_illustrations_no_images(test_db):
    """has_illustrations should be False when all scenes have null image_url"""
    story = save_story(
        db=test_db,
        story_id="illust-none-test",
        title="No Images",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={"scenes": [{"beat_index": 0, "image_url": "/old.png"}]},
    )
    short_id = story.short_id
    assert story.has_illustrations is True

    # Update with all-null images
    new_scene_data = {
        "scenes": [{"beat_index": 0, "image_url": None}],
    }
    updated = update_story_illustrations(test_db, short_id, new_scene_data)
    assert updated.has_illustrations is False


def test_update_story_illustrations_with_cover(test_db):
    """update_story_illustrations optionally updates cover_image_path"""
    story = save_story(
        db=test_db,
        story_id="illust-cover-test",
        title="Cover Test",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
    )
    short_id = story.short_id

    scene_data = {"scenes": [{"beat_index": 0, "image_url": "/img.png"}]}
    updated = update_story_illustrations(
        test_db, short_id, scene_data, cover_image_path="/new/cover.png"
    )
    assert updated.cover_image_path == "/new/cover.png"


def test_update_story_illustrations_not_found(test_db):
    """update_story_illustrations returns None for non-existent story"""
    result = update_story_illustrations(test_db, "notfound", {"scenes": []})
    assert result is None
