"""Tests for video transcoder module."""
import pytest


def test_video_transcoder_imports():
    """Verify video_transcoder module can be imported (catches Python 3.9 syntax issues)."""
    from app.utils.video_transcoder import generate_story_video
    assert callable(generate_story_video)
