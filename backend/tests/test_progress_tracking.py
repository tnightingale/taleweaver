"""
Tests that pipeline progress advances during story generation.

The progress field in job_state must advance at each stage transition,
not stay stuck at 0%.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.db.crud import create_job_state, get_job_state, update_job_stage


def test_update_job_stage_with_progress_sets_both(test_db):
    """update_job_stage should set both stage and progress when progress is passed."""
    job = create_job_state(test_db, "progress-test-1", ["writing", "synthesizing"])

    update_job_stage(test_db, "progress-test-1", "synthesizing", progress=50.0)

    refreshed = get_job_state(test_db, "progress-test-1")
    assert refreshed.current_stage == "synthesizing"
    assert refreshed.progress == 50.0


def test_update_job_stage_without_progress_preserves_value(test_db):
    """update_job_stage without progress should NOT reset it to 0."""
    job = create_job_state(test_db, "progress-test-2", ["writing", "synthesizing"])
    # Simulate a node setting progress mid-stage
    job.progress = 42.0
    test_db.commit()

    update_job_stage(test_db, "progress-test-2", "synthesizing")

    refreshed = get_job_state(test_db, "progress-test-2")
    assert refreshed.progress == 42.0, "Stage transition must not reset progress"


def test_pipeline_loop_advances_progress(test_db):
    """
    The pipeline loop in run_pipeline should pass a progress value
    when calling update_job_stage so the frontend sees advancement.
    """
    import inspect
    from app.routes import story

    source = inspect.getsource(story.run_pipeline)

    # The pipeline loop must call update_job_stage with a progress parameter
    # Look for the pattern: update_job_stage(db, job_id, next_stage, progress=...)
    assert "progress=" in source, (
        "run_pipeline must pass progress= to update_job_stage() "
        "so the frontend progress bar advances during generation"
    )
