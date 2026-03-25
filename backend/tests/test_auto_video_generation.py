"""Tests for automatic video generation after story/illustration creation."""
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.db.models import Story, JobState


def _create_illustrated_story(db, user_id, storage_dir, with_video=False):
    """Helper to create an illustrated story with files on disk."""
    story_id = str(uuid.uuid4())
    short_id = "test1234"
    story_dir = storage_dir / "stories" / story_id
    story_dir.mkdir(parents=True)

    audio_path = story_dir / "audio.mp3"
    audio_path.write_bytes(b"fake audio")

    scene_path = story_dir / "scene_0.png"
    scene_path.write_bytes(b"fake image")

    video_path = None
    if with_video:
        vp = story_dir / "video.mp4"
        vp.write_bytes(b"fake video")
        video_path = str(vp)

    story = Story(
        id=story_id,
        short_id=short_id,
        title="Test Story",
        kid_name="Test",
        kid_age=5,
        story_type="custom",
        mood="exciting",
        length="short",
        transcript="Once upon a time...",
        duration_seconds=60,
        audio_path=str(audio_path),
        has_illustrations=True,
        art_style="watercolor_dream",
        scene_data={
            "scenes": [
                {
                    "timestamp_start": 0,
                    "timestamp_end": 60,
                    "image_path": str(scene_path),
                }
            ]
        },
        video_path=video_path,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )
    db.add(story)
    db.commit()
    return story


def test_maybe_enqueue_video_exists(test_db, test_user):
    """_maybe_enqueue_video can be imported and called."""
    from app.jobs.tasks import _maybe_enqueue_video
    assert callable(_maybe_enqueue_video)


@patch("app.jobs.tasks.generate_video_task")
def test_maybe_enqueue_video_for_illustrated_story(mock_task, test_db, test_user, tmp_path):
    """Enqueues video generation for an illustrated story without video."""
    from app.jobs.tasks import _maybe_enqueue_video

    story = _create_illustrated_story(test_db, test_user.id, tmp_path)
    result = _maybe_enqueue_video(story.id)

    assert result is True
    mock_task.assert_called_once()
    args = mock_task.call_args[0]
    assert args[1] == story.short_id  # short_id
    assert args[2] == story.id  # story_id


@patch("app.jobs.tasks.generate_video_task")
def test_maybe_enqueue_video_skips_if_video_exists(mock_task, test_db, test_user, tmp_path):
    """Does NOT enqueue if video already exists."""
    from app.jobs.tasks import _maybe_enqueue_video

    story = _create_illustrated_story(test_db, test_user.id, tmp_path, with_video=True)
    result = _maybe_enqueue_video(story.id)

    assert result is False
    mock_task.assert_not_called()


@patch("app.jobs.tasks.generate_video_task")
def test_maybe_enqueue_video_skips_if_job_in_progress(mock_task, test_db, test_user, tmp_path):
    """Does NOT enqueue if there's already an in-progress video job."""
    from app.jobs.tasks import _maybe_enqueue_video

    story = _create_illustrated_story(test_db, test_user.id, tmp_path)

    # Create an in-progress video job
    job = JobState(
        job_id=str(uuid.uuid4()),
        status="processing",
        current_stage="generating_video",
        stages='["generating_video"]',
        short_id=story.short_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(job)
    test_db.commit()

    result = _maybe_enqueue_video(story.id)

    assert result is False
    mock_task.assert_not_called()


@patch("app.jobs.tasks.generate_video_task")
def test_maybe_enqueue_video_skips_non_illustrated(mock_task, test_db, test_user, tmp_path):
    """Does NOT enqueue for stories without illustrations."""
    from app.jobs.tasks import _maybe_enqueue_video

    story_id = str(uuid.uuid4())
    story_dir = tmp_path / "stories" / story_id
    story_dir.mkdir(parents=True)
    audio_path = story_dir / "audio.mp3"
    audio_path.write_bytes(b"fake audio")

    story = Story(
        id=story_id,
        short_id="noill123",
        title="No Illustrations",
        kid_name="Test",
        kid_age=5,
        story_type="custom",
        mood="exciting",
        length="short",
        transcript="A story.",
        duration_seconds=30,
        audio_path=str(audio_path),
        has_illustrations=False,
        user_id=test_user.id,
        created_at=datetime.utcnow(),
    )
    test_db.add(story)
    test_db.commit()

    result = _maybe_enqueue_video(story.id)

    assert result is False
    mock_task.assert_not_called()


@patch("app.jobs.tasks.generate_video_task")
def test_backfill_videos_endpoint(mock_task, test_db, test_client, test_user, tmp_path):
    """POST /api/admin/backfill-videos enqueues jobs for illustrated stories without video."""
    from app.jobs.tasks import _maybe_enqueue_video

    # Patch storage path so stories are found
    with patch("app.jobs.tasks._maybe_enqueue_video", wraps=_maybe_enqueue_video) as mock_enqueue:
        story = _create_illustrated_story(test_db, test_user.id, tmp_path)

        response = test_client.post("/api/admin/backfill-videos")
        assert response.status_code == 200
        data = response.json()
        assert data["candidates"] >= 1
