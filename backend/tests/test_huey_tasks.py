"""
Tests for huey background job infrastructure.

Verifies that the huey app is configured correctly and that
the story generation task can be defined, serialized, and called.
"""
import pytest


def test_huey_app_uses_sqlite_storage():
    """huey instance must use SqliteHuey backed by /storage/huey.db."""
    from app.jobs.huey_app import huey
    from huey import SqliteHuey

    assert isinstance(huey, SqliteHuey), (
        f"huey instance is {type(huey).__name__}, must be SqliteHuey"
    )


def test_generate_story_task_is_registered():
    """generate_story_task must be a registered huey task."""
    from app.jobs.tasks import generate_story_task

    # huey tasks are decorated functions with a .call_local() method
    assert hasattr(generate_story_task, "call_local"), (
        "generate_story_task must be a @huey.task()-decorated function"
    )


def test_build_state_from_params_custom_story():
    """_build_state_from_params should reconstruct a valid pipeline state dict."""
    from app.jobs.tasks import build_state_from_params

    params = {
        "kid_name": "Arjun",
        "kid_age": 7,
        "kid_details": "Loves dinosaurs",
        "story_type": "custom",
        "genre": "adventure",
        "description": "A dinosaur adventure",
        "event_id": None,
        "event_data": None,
        "mood": "exciting",
        "length": "medium",
        "art_style": None,
        "custom_art_style_prompt": None,
    }

    state = build_state_from_params("test-job-123", params)

    assert state["job_id"] == "test-job-123"
    assert state["kid_name"] == "Arjun"
    assert state["kid_age"] == 7
    assert state["story_type"] == "custom"
    assert state["genre"] == "adventure"
    assert state["mood"] == "exciting"
    # Pipeline output fields should be initialized empty
    assert state["story_text"] == ""
    assert state["title"] == ""
    assert state["segments"] == []
    assert state["audio_segments"] == []
    assert state["final_audio"] == b""
    assert state["final_audio_path"] is None
    assert state["duration_seconds"] == 0
    assert state["error"] is None
    assert state["scenes"] is None


def test_build_state_from_params_historical_story():
    """_build_state_from_params should handle historical story params."""
    from app.jobs.tasks import build_state_from_params

    params = {
        "kid_name": "Maya",
        "kid_age": 9,
        "kid_details": "",
        "story_type": "historical",
        "genre": None,
        "description": None,
        "event_id": "moon-landing",
        "event_data": {"id": "moon-landing", "title": "Moon Landing"},
        "mood": "exciting",
        "length": "long",
        "art_style": "watercolor",
        "custom_art_style_prompt": None,
    }

    state = build_state_from_params("test-job-456", params)

    assert state["story_type"] == "historical"
    assert state["event_id"] == "moon-landing"
    assert state["event_data"]["title"] == "Moon Landing"
    assert state["art_style"] == "watercolor"


def test_story_params_are_json_serializable():
    """
    All task arguments must be JSON-serializable since they're persisted
    to huey's SQLite queue. No bytes, no db sessions, no callables.
    """
    import json

    params = {
        "kid_name": "Test",
        "kid_age": 5,
        "kid_details": "Likes cats",
        "story_type": "custom",
        "genre": "fantasy",
        "description": "A cat story",
        "event_id": None,
        "event_data": None,
        "mood": "funny",
        "length": "short",
        "art_style": None,
        "custom_art_style_prompt": None,
    }

    # Must not raise
    serialized = json.dumps({"job_id": "test-123", "story_params": params})
    deserialized = json.loads(serialized)
    assert deserialized["story_params"]["kid_name"] == "Test"
