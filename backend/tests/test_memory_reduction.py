"""
Tests for memory reduction in the story generation pipeline.

Key invariant: large binary data (final MP3 audio) should be written directly
to disk rather than carried through LangGraph state as bytes objects.
"""
import io
import pytest
import tempfile
from pathlib import Path
from pydub.generators import Sine


def _make_test_audio(duration_ms: int = 500) -> bytes:
    """Generate a short sine wave as MP3 bytes."""
    tone = Sine(440).to_audio_segment(duration=duration_ms)
    buf = io.BytesIO()
    tone.export(buf, format="mp3")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_audio_stitcher_writes_to_disk(tmp_path):
    """
    audio_stitcher should write the final MP3 to disk and return a file path,
    NOT return raw bytes in state. This prevents holding 10-50MB in memory.
    """
    from app.graph.nodes.audio_stitcher import audio_stitcher
    import app.config as config_module
    original_storage = config_module.settings.storage_path
    config_module.settings.storage_path = tmp_path

    try:
        segments = [_make_test_audio(500) for _ in range(3)]
        state = {
            "audio_segments": segments,
            "job_id": "test-job-123",
        }
        result = await audio_stitcher(state)

        # Must return a file path, not raw bytes
        assert "final_audio_path" in result, (
            "audio_stitcher must return 'final_audio_path' (str) instead of "
            "'final_audio' (bytes) to avoid holding large MP3 in memory"
        )
        assert isinstance(result["final_audio_path"], str)

        # File must actually exist on disk
        audio_path = Path(result["final_audio_path"])
        assert audio_path.exists(), f"Audio file not found at {audio_path}"
        assert audio_path.stat().st_size > 0

        # Must still return duration
        assert "duration_seconds" in result
        assert result["duration_seconds"] > 0

        # Must NOT return raw bytes
        assert "final_audio" not in result, (
            "audio_stitcher should not return 'final_audio' bytes — "
            "write to disk instead to reduce memory usage"
        )
    finally:
        config_module.settings.storage_path = original_storage


@pytest.mark.asyncio
async def test_audio_stitcher_writes_to_story_directory(tmp_path):
    """Audio file should be written to /storage/stories/{job_id}/audio.mp3."""
    from app.graph.nodes.audio_stitcher import audio_stitcher
    import app.config as config_module
    original_storage = config_module.settings.storage_path
    config_module.settings.storage_path = tmp_path

    try:
        job_id = "test-job-456"
        segments = [_make_test_audio(300)]
        state = {
            "audio_segments": segments,
            "job_id": job_id,
        }
        result = await audio_stitcher(state)

        expected_path = tmp_path / "stories" / job_id / "audio.mp3"
        assert Path(result["final_audio_path"]) == expected_path
        assert expected_path.exists()
    finally:
        config_module.settings.storage_path = original_storage


def test_save_story_uses_existing_audio_file(test_db, tmp_path):
    """
    save_story should accept audio_path (existing file on disk) instead of
    requiring audio_bytes to be passed through memory.
    """
    from app.db.crud import save_story
    import app.config as config_module
    original_storage = config_module.settings.storage_path
    config_module.settings.storage_path = tmp_path

    try:
        # Pre-create the audio file (as audio_stitcher would)
        job_id = "test-story-789"
        story_dir = tmp_path / "stories" / job_id
        story_dir.mkdir(parents=True)
        audio_file = story_dir / "audio.mp3"
        audio_file.write_bytes(b"pre-existing audio data")

        story = save_story(
            db=test_db,
            story_id=job_id,
            title="Disk Audio Test",
            kid_name="Test",
            kid_age=5,
            story_type="custom",
            transcript="test",
            duration_seconds=60,
            audio_path=str(audio_file),
        )

        assert story.audio_path == str(audio_file)
        # The file should still exist (not moved or deleted)
        assert audio_file.exists()
    finally:
        config_module.settings.storage_path = original_storage
