"""
Tests for illustration regeneration endpoint and CRUD
"""
import pytest
from unittest.mock import patch, MagicMock

from app.db.crud import save_story, get_story_by_short_id


def test_regenerate_endpoint_returns_job(test_db, test_client):
    """POST /api/stories/{short_id}/regenerate-illustrations creates a regen job"""
    story = save_story(
        db=test_db,
        story_id="regen-test-1",
        title="Test Story",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img.png", "illustration_prompt": "Prompt 0",
                 "generation_metadata": {"succeeded": True}},
                {"beat_index": 1, "image_url": None, "illustration_prompt": "Prompt 1",
                 "generation_metadata": {"succeeded": False, "error": "timeout"}},
            ],
            "art_style_prompt": "watercolor",
        },
    )

    with patch("app.jobs.tasks.regenerate_illustrations_task") as mock_task:
        response = test_client.post(f"/api/stories/{story.short_id}/regenerate-illustrations")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["failed_count"] == 1
    assert data["total_scenes"] == 2
    assert "job_id" in data
    mock_task.assert_called_once()


def test_regenerate_endpoint_all_present(test_db, test_client):
    """Should return ok message when all illustrations already present"""
    story = save_story(
        db=test_db,
        story_id="regen-all-ok",
        title="All Good",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img0.png",
                 "generation_metadata": {"succeeded": True}},
                {"beat_index": 1, "image_url": "/img1.png",
                 "generation_metadata": {"succeeded": True}},
            ],
        },
    )

    response = test_client.post(f"/api/stories/{story.short_id}/regenerate-illustrations")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "already present" in data["message"]


def test_regenerate_endpoint_no_art_style(test_db, test_client):
    """Should return 400 when story has no art style"""
    story = save_story(
        db=test_db,
        story_id="regen-no-style",
        title="No Style",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
    )

    response = test_client.post(f"/api/stories/{story.short_id}/regenerate-illustrations")
    assert response.status_code == 400
    assert "art style" in response.json()["detail"].lower()


def test_regenerate_endpoint_not_found(test_client):
    """Should return 404 for non-existent story"""
    response = test_client.post("/api/stories/notfound/regenerate-illustrations")
    assert response.status_code == 404


def test_regenerate_endpoint_no_scene_data(test_db, test_client):
    """Should return 400 when story has no scene data"""
    story = save_story(
        db=test_db,
        story_id="regen-no-scenes",
        title="No Scenes",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
    )

    response = test_client.post(f"/api/stories/{story.short_id}/regenerate-illustrations")
    assert response.status_code == 400
    assert "scene data" in response.json()["detail"].lower()


# ── mode="missing" backward compatibility ──

def test_regenerate_missing_with_explicit_mode(test_db, test_client):
    """mode=missing with explicit body works same as no body"""
    story = save_story(
        db=test_db,
        story_id="regen-missing-explicit",
        title="Missing Explicit",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img.png", "illustration_prompt": "P0",
                 "generation_metadata": {"succeeded": True}},
                {"beat_index": 1, "image_url": None, "illustration_prompt": "P1",
                 "generation_metadata": {"succeeded": False}},
            ],
            "art_style_prompt": "watercolor",
        },
    )

    with patch("app.jobs.tasks.regenerate_illustrations_task") as mock_task:
        response = test_client.post(
            f"/api/stories/{story.short_id}/regenerate-illustrations",
            json={"mode": "missing"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["failed_count"] == 1
    mock_task.assert_called_once()


# ── mode="single" ──

def test_regenerate_single_scene(test_db, test_client):
    """mode=single regenerates a specific scene by index"""
    story = save_story(
        db=test_db,
        story_id="regen-single",
        title="Single Scene",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img0.png", "illustration_prompt": "P0",
                 "generation_metadata": {"succeeded": True}},
                {"beat_index": 1, "image_url": "/img1.png", "illustration_prompt": "P1",
                 "generation_metadata": {"succeeded": True}},
            ],
            "art_style_prompt": "watercolor",
        },
    )

    with patch("app.jobs.tasks.regenerate_illustrations_task") as mock_task:
        response = test_client.post(
            f"/api/stories/{story.short_id}/regenerate-illustrations",
            json={"mode": "single", "scene_index": 1},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["failed_count"] == 1
    # Verify only the specified index is passed
    call_args = mock_task.call_args
    assert call_args[0][5] == [1]  # failed_indices positional arg


def test_regenerate_single_requires_scene_index(test_db, test_client):
    """mode=single without scene_index returns 400"""
    story = save_story(
        db=test_db,
        story_id="regen-single-noidx",
        title="Single No Idx",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img.png", "illustration_prompt": "P",
                 "generation_metadata": {"succeeded": True}},
            ],
            "art_style_prompt": "watercolor",
        },
    )

    response = test_client.post(
        f"/api/stories/{story.short_id}/regenerate-illustrations",
        json={"mode": "single"},
    )
    assert response.status_code == 400
    assert "scene_index" in response.json()["detail"].lower()


def test_regenerate_single_out_of_range(test_db, test_client):
    """mode=single with out-of-range scene_index returns 400"""
    story = save_story(
        db=test_db,
        story_id="regen-single-oor",
        title="Single OOR",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img.png", "illustration_prompt": "P",
                 "generation_metadata": {"succeeded": True}},
            ],
            "art_style_prompt": "watercolor",
        },
    )

    response = test_client.post(
        f"/api/stories/{story.short_id}/regenerate-illustrations",
        json={"mode": "single", "scene_index": 5},
    )
    assert response.status_code == 400
    assert "out of range" in response.json()["detail"].lower()


# ── mode="all" ──

def test_regenerate_all_scenes(test_db, test_client):
    """mode=all regenerates every scene regardless of status"""
    story = save_story(
        db=test_db,
        story_id="regen-all",
        title="Regen All",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img0.png", "illustration_prompt": "P0",
                 "generation_metadata": {"succeeded": True}},
                {"beat_index": 1, "image_url": "/img1.png", "illustration_prompt": "P1",
                 "generation_metadata": {"succeeded": True}},
                {"beat_index": 2, "image_url": "/img2.png", "illustration_prompt": "P2",
                 "generation_metadata": {"succeeded": True}},
            ],
            "art_style_prompt": "watercolor",
        },
    )

    with patch("app.jobs.tasks.regenerate_illustrations_task") as mock_task:
        response = test_client.post(
            f"/api/stories/{story.short_id}/regenerate-illustrations",
            json={"mode": "all"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["failed_count"] == 3  # all scenes
    call_args = mock_task.call_args
    assert call_args[0][5] == [0, 1, 2]  # all indices


def test_regenerate_all_with_new_art_style(test_db, test_client):
    """mode=all with art_style updates the story's art_style"""
    story = save_story(
        db=test_db,
        story_id="regen-all-newstyle",
        title="New Style",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img.png", "illustration_prompt": "P",
                 "generation_metadata": {"succeeded": True}},
            ],
            "art_style_prompt": "watercolor",
        },
    )

    with patch("app.jobs.tasks.regenerate_illustrations_task") as mock_task:
        response = test_client.post(
            f"/api/stories/{story.short_id}/regenerate-illustrations",
            json={"mode": "all", "art_style": "digital_fantasy"},
        )

    assert response.status_code == 200
    # Verify new art_style is passed to the task
    call_args = mock_task.call_args
    assert call_args[0][3] == "digital_fantasy"  # art_style positional arg


# ── mode="add" ──

def test_add_illustrations_to_story_without_any(test_db, test_client):
    """mode=add works for stories with no illustrations"""
    story = save_story(
        db=test_db,
        story_id="regen-add",
        title="No Illustrations",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="A test story transcript.",
        duration_seconds=100,
        audio_bytes=b"audio",
    )

    with patch("app.jobs.tasks.add_illustrations_task") as mock_task:
        response = test_client.post(
            f"/api/stories/{story.short_id}/regenerate-illustrations",
            json={"mode": "add", "art_style": "watercolor_dream"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    mock_task.assert_called_once()


def test_add_illustrations_rejected_when_already_has_illustrations(test_db, test_client):
    """mode=add returns 400 when story already has scene_data"""
    story = save_story(
        db=test_db,
        story_id="regen-add-exists",
        title="Has Illustrations",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {"beat_index": 0, "image_url": "/img.png", "illustration_prompt": "P",
                 "generation_metadata": {"succeeded": True}},
            ],
        },
    )

    response = test_client.post(
        f"/api/stories/{story.short_id}/regenerate-illustrations",
        json={"mode": "add", "art_style": "watercolor_dream"},
    )
    assert response.status_code == 400
    assert "already has" in response.json()["detail"].lower()


def test_add_illustrations_requires_art_style(test_db, test_client):
    """mode=add without art_style returns 400"""
    story = save_story(
        db=test_db,
        story_id="regen-add-nostyle",
        title="Add No Style",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
    )

    response = test_client.post(
        f"/api/stories/{story.short_id}/regenerate-illustrations",
        json={"mode": "add"},
    )
    assert response.status_code == 400
    assert "art_style" in response.json()["detail"].lower()


def test_invalid_mode_returns_400(test_db, test_client):
    """Invalid mode returns 400"""
    story = save_story(
        db=test_db,
        story_id="regen-invalid-mode",
        title="Invalid Mode",
        kid_name="Test",
        kid_age=7,
        story_type="custom",
        transcript="...",
        duration_seconds=100,
        audio_bytes=b"audio",
        art_style="watercolor_dream",
        scene_data={"scenes": [{"beat_index": 0, "image_url": "/img.png",
                                "illustration_prompt": "P", "generation_metadata": {"succeeded": True}}]},
    )

    response = test_client.post(
        f"/api/stories/{story.short_id}/regenerate-illustrations",
        json={"mode": "invalid"},
    )
    assert response.status_code == 400
