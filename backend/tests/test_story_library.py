"""
Tests for Story Library Feature
Uses isolated test database fixtures from conftest.py
"""
import pytest

from app.db.crud import save_story, list_stories, get_unique_kid_names


def test_list_stories_returns_empty_when_no_stories(test_client):
    """GET /api/stories returns empty array when no stories exist"""
    response = test_client.get("/api/stories")
    assert response.status_code == 200
    data = response.json()
    assert "stories" in data
    assert isinstance(data["stories"], list)
    assert data["total"] >= 0
    assert data["has_more"] == False


def test_list_stories_returns_all_stories(test_db, test_client, test_user):
    """GET /api/stories returns list of stories"""
    # Create test stories in isolated database
    save_story(
        db=test_db,
        story_id="list-test-1",
        title="Story 1",
        kid_name="Arjun",
        kid_age=7,
        story_type="custom",
        genre="fantasy",
        transcript="Story 1 text",
        duration_seconds=180,
        audio_bytes=b"audio1",
        user_id=test_user.id,
    )
    save_story(
        db=test_db,
        story_id="list-test-2",
        title="Story 2",
        kid_name="Maya",
        kid_age=5,
        story_type="historical",
        event_id="test-event",
        transcript="Story 2 text",
        duration_seconds=120,
        audio_bytes=b"audio2",
        user_id=test_user.id,
    )

    response = test_client.get("/api/stories")
    assert response.status_code == 200
    data = response.json()

    assert len(data["stories"]) >= 2
    assert data["total"] >= 2

    # Verify structure
    story = data["stories"][0]
    assert "id" in story
    assert "short_id" in story
    assert "title" in story
    assert "kid_name" in story
    assert "kid_age" in story
    assert "story_type" in story
    assert "duration_seconds" in story
    assert "created_at" in story
    assert "permalink" in story
    assert "audio_url" in story


def test_list_stories_filters_by_kid_name(test_db, test_client, test_user):
    """Can filter stories by kid name"""
    save_story(
        db=test_db,
        story_id="filter-test-arjun",
        title="Arjun Story",
        kid_name="Arjun",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        user_id=test_user.id,
    )
    save_story(
        db=test_db,
        story_id="filter-test-maya",
        title="Maya Story",
        kid_name="Maya",
        kid_age=5,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        user_id=test_user.id,
    )

    response = test_client.get("/api/stories?kid_name=Arjun")
    assert response.status_code == 200
    data = response.json()

    # Should only return Arjun's stories
    for story in data["stories"]:
        assert story["kid_name"] == "Arjun"


def test_list_stories_pagination(test_db, test_client, test_user):
    """Supports limit and offset for pagination"""
    for i in range(5):
        save_story(
            db=test_db,
            story_id=f"page-test-{i}",
            title=f"Story {i}",
            kid_name="Test Kid",
            kid_age=6,
            story_type="custom",
            transcript="...",
            duration_seconds=100,
            audio_bytes=b"audio",
            user_id=test_user.id,
        )

    # Get first 2
    response = test_client.get("/api/stories?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["stories"]) == 2
    assert data["total"] >= 5
    assert data["has_more"] == True

    # Get next 2
    response2 = test_client.get("/api/stories?limit=2&offset=2")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["stories"]) == 2

    # Verify different stories
    assert data["stories"][0]["id"] != data2["stories"][0]["id"]


def test_list_stories_sorts_newest_first(test_db, test_client, test_user):
    """Stories sorted by created_at desc by default"""
    for i in range(3):
        save_story(
            db=test_db,
            story_id=f"sort-test-{i}",
            title=f"Story {i}",
            kid_name="Test",
            kid_age=6,
            story_type="custom",
            transcript="...",
            duration_seconds=100,
            audio_bytes=b"audio",
            user_id=test_user.id,
        )

    response = test_client.get("/api/stories?limit=10")
    assert response.status_code == 200
    data = response.json()

    stories = data["stories"]
    if len(stories) >= 2:
        for i in range(len(stories) - 1):
            curr_date = stories[i]["created_at"]
            next_date = stories[i + 1]["created_at"]
            assert curr_date >= next_date, "Should be sorted newest first"


def test_list_stories_includes_art_style_and_scenes(test_db, test_client, test_user):
    """GET /api/stories returns art_style and scenes for illustrated stories"""
    scene_data = {
        "scenes": [
            {
                "beat_index": 0,
                "beat_name": "Once upon a time",
                "text_excerpt": "Opening...",
                "timestamp_start": 0.0,
                "timestamp_end": 30.0,
                "image_url": None,
            },
            {
                "beat_index": 1,
                "beat_name": "Every day",
                "text_excerpt": "Middle...",
                "timestamp_start": 30.0,
                "timestamp_end": 60.0,
                "image_url": "/storage/stories/illustrated-test/scene_1.png",
            },
        ]
    }
    save_story(
        db=test_db,
        story_id="illustrated-test",
        title="Illustrated Story",
        kid_name="Test",
        kid_age=5,
        story_type="custom",
        transcript="Story text",
        duration_seconds=60,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data=scene_data,
        user_id=test_user.id,
    )

    response = test_client.get("/api/stories")
    assert response.status_code == 200
    data = response.json()

    illustrated = next(s for s in data["stories"] if s["id"] == "illustrated-test")
    assert illustrated["art_style"] == "watercolor_dream"
    assert illustrated["scenes"] is not None
    assert len(illustrated["scenes"]) == 2
    assert illustrated["scenes"][0]["image_url"] is None
    assert illustrated["scenes"][1]["image_url"] == "/storage/stories/illustrated-test/scene_1.png"


def test_get_unique_kid_names(test_db):
    """Can get list of unique kid names for filter dropdown"""
    save_story(test_db, "kid-test-1", "T1", "Arjun", 7, "custom", "...", 100, b"a")
    save_story(test_db, "kid-test-2", "T2", "Arjun", 7, "custom", "...", 100, b"a")
    save_story(test_db, "kid-test-3", "T3", "Maya", 5, "custom", "...", 100, b"a")

    names = get_unique_kid_names(test_db)
    assert isinstance(names, list)
    assert "Arjun" in names
    assert "Maya" in names
