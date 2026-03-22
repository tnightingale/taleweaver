"""
Tests for Illustration Generator Resilience (TDD RED Phase)
Testing partial failure handling and error recovery
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO
from PIL import Image

from app.graph.state import StoryState
from app.graph.nodes.illustration_generator import illustration_generator


def create_fake_image_bytes():
    """Create minimal valid PNG bytes for testing"""
    img = Image.new('RGB', (10, 10), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_illustration_generator_continues_after_single_failure():
    """Should continue generating images after one fails"""
    # Mock provider to fail on image 2, succeed on others
    call_count = [0]
    fake_png = create_fake_image_bytes()
    
    async def mock_generate(prompt, art_style, **kwargs):
        call_count[0] += 1
        if call_count[0] == 3:  # Fail on 3rd call (index 2)
            raise Exception("Simulated API error for image 2")
        return fake_png
    
    mock_provider = MagicMock()
    mock_provider.generate_image = mock_generate
    mock_provider.get_provider_info = MagicMock(return_value={"name": "Test", "model": "test-model"})
    
    # Create state with 5 scenes
    state: StoryState = {
        "job_id": "test-partial-1",
        "kid_name": "Test",
        "kid_age": 7,
        "kid_details": "",
        "story_type": "custom",
        "genre": "fantasy",
        "description": "Test",
        "event_id": None,
        "event_data": None,
        "mood": None,
        "length": "short",
        "art_style": "watercolor_dream",
        "custom_art_style_prompt": None,
        "story_text": "Test story",
        "title": "Test",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": [
            {
                "beat_index": i,
                "beat_name": f"Beat {i}",
                "text_excerpt": f"Text {i}",
                "illustration_prompt": f"Prompt {i}",
                "timestamp_start": 0.0,
                "timestamp_end": 10.0,
                "word_count": 50,
                "image_path": None,
                "image_url": None,
                "generation_metadata": None,
            }
            for i in range(5)
        ],
        "character_description": "Test character",
    }
    
    with patch("app.graph.nodes.illustration_generator.get_illustration_provider", return_value=mock_provider):
        with patch("app.graph.nodes.illustration_generator.save_illustration", return_value="/test/path.png"):
            result = await illustration_generator(state)
    
    # Verify partial success
    assert "scenes" in result
    scenes = result["scenes"]
    
    # Scenes 0, 1, 3, 4 should have images (image 2 failed)
    assert scenes[0]["image_url"] is not None, "Scene 0 should have image"
    assert scenes[1]["image_url"] is not None, "Scene 1 should have image"
    assert scenes[2]["image_url"] is None, "Scene 2 should NOT have image (failed)"
    assert scenes[3]["image_url"] is not None, "Scene 3 should have image (continued after failure)"
    assert scenes[4]["image_url"] is not None, "Scene 4 should have image"
    
    # Verify partial success flag
    assert result.get("partial_illustrations") is True
    assert result.get("successful_count") == 4
    assert result.get("failed_count") == 1


@pytest.mark.asyncio
async def test_illustration_generator_tracks_each_error():
    """Should track detailed error information for each failure"""
    call_count = [0]
    fake_png = create_fake_image_bytes()
    
    async def mock_generate(prompt, art_style, **kwargs):
        call_count[0] += 1
        if call_count[0] in [2, 4]:  # Fail on images 1 and 3
            raise Exception(f"API error {call_count[0]}")
        return fake_png
    
    mock_provider = MagicMock()
    mock_provider.generate_image = mock_generate
    mock_provider.get_provider_info = MagicMock(return_value={"name": "Test", "model": "test-model"})
    
    state: StoryState = {
        "job_id": "test-errors",
        "kid_name": "Test",
        "kid_age": 7,
        "kid_details": "",
        "story_type": "custom",
        "genre": "fantasy",
        "description": "Test",
        "event_id": None,
        "event_data": None,
        "mood": None,
        "length": None,
        "art_style": "modern_flat",
        "custom_art_style_prompt": None,
        "story_text": "Test",
        "title": "Test",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": [
            {
                "beat_index": i,
                "beat_name": f"Beat {i}",
                "text_excerpt": f"Text {i}",
                "illustration_prompt": f"Prompt {i}",
                "timestamp_start": 0.0,
                "timestamp_end": 10.0,
                "word_count": 50,
                "image_path": None,
                "image_url": None,
                "generation_metadata": None,
            }
            for i in range(5)
        ],
        "character_description": None,
    }
    
    with patch("app.graph.nodes.illustration_generator.get_illustration_provider", return_value=mock_provider):
        with patch("app.graph.nodes.illustration_generator.save_illustration", return_value="/test/path.png"):
            result = await illustration_generator(state)
    
    # Verify errors are tracked
    assert "errors" in result
    errors = result["errors"]
    assert len(errors) == 2, "Should track 2 errors"
    
    # Check first error details
    assert errors[0]["index"] == 1
    assert "API error 2" in errors[0]["error"]
    
    # Check second error details
    assert errors[1]["index"] == 3
    assert "API error 4" in errors[1]["error"]
    
    # Verify successful images
    assert result["successful_count"] == 3
    assert result["failed_count"] == 2


@pytest.mark.asyncio
async def test_illustration_generator_complete_failure():
    """Should handle complete failure gracefully (all images fail)"""
    async def mock_generate_always_fails(prompt, art_style, **kwargs):
        raise Exception("Persistent API error")
    
    mock_provider = MagicMock()
    mock_provider.generate_image = mock_generate_always_fails
    mock_provider.get_provider_info = MagicMock(return_value={"name": "Test", "model": "test-model"})
    
    state: StoryState = {
        "job_id": "test-complete-fail",
        "kid_name": "Test",
        "kid_age": 7,
        "kid_details": "",
        "story_type": "custom",
        "genre": "fantasy",
        "description": "Test",
        "event_id": None,
        "event_data": None,
        "mood": None,
        "length": None,
        "art_style": "watercolor_dream",
        "custom_art_style_prompt": None,
        "story_text": "Test",
        "title": "Test",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": [
            {
                "beat_index": 0,
                "beat_name": "Test",
                "text_excerpt": "Text",
                "illustration_prompt": "Prompt",
                "timestamp_start": 0.0,
                "timestamp_end": 10.0,
                "word_count": 50,
                "image_path": None,
                "image_url": None,
                "generation_metadata": None,
            }
        ],
        "character_description": None,
    }
    
    with patch("app.graph.nodes.illustration_generator.get_illustration_provider", return_value=mock_provider):
        result = await illustration_generator(state)
    
    # Should return error but not crash
    assert "error" in result
    assert "scenes" in result
    assert result["scenes"][0]["image_url"] is None
    assert "Illustration generation failed" in result["error"]


@pytest.mark.asyncio
async def test_illustration_generator_logs_detailed_errors(caplog):
    """Should log detailed error information for debugging"""
    import logging
    caplog.set_level(logging.ERROR)
    
    async def mock_generate_fails(prompt, art_style, **kwargs):
        raise ValueError("Invalid prompt format")
    
    mock_provider = MagicMock()
    mock_provider.generate_image = mock_generate_fails
    mock_provider.get_provider_info = MagicMock(return_value={"name": "Test", "model": "test-model"})
    
    state: StoryState = {
        "job_id": "test-logging",
        "kid_name": "Test",
        "kid_age": 7,
        "kid_details": "",
        "story_type": "custom",
        "genre": "fantasy",
        "description": "Test",
        "event_id": None,
        "event_data": None,
        "mood": None,
        "length": None,
        "art_style": "classic_storybook",
        "custom_art_style_prompt": None,
        "story_text": "Test",
        "title": "Test",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": [
            {
                "beat_index": 0,
                "beat_name": "Once upon a time",
                "text_excerpt": "Text",
                "illustration_prompt": "Test prompt",
                "timestamp_start": 0.0,
                "timestamp_end": 10.0,
                "word_count": 50,
                "image_path": None,
                "image_url": None,
                "generation_metadata": None,
            }
        ],
        "character_description": None,
    }
    
    with patch("app.graph.nodes.illustration_generator.get_illustration_provider", return_value=mock_provider):
        result = await illustration_generator(state)
    
    # Verify detailed logging
    log_text = caplog.text
    assert "Failed to generate illustration" in log_text
    assert "ValueError" in log_text or "Error type" in log_text
    assert "Invalid prompt format" in log_text


@pytest.mark.asyncio
async def test_illustration_generator_preserves_successful_metadata():
    """Should preserve generation metadata for successful images even if others fail"""
    call_count = [0]
    fake_png = create_fake_image_bytes()
    
    async def mock_generate_partial(prompt, art_style, **kwargs):
        call_count[0] += 1
        if call_count[0] > 2:  # Fail after 2 successes
            raise Exception("Quota exceeded")
        return fake_png
    
    mock_provider = MagicMock()
    mock_provider.generate_image = mock_generate_partial
    mock_provider.get_provider_info = MagicMock(return_value={"name": "NanoBanana", "model": "gemini"})
    
    state: StoryState = {
        "job_id": "test-metadata",
        "kid_name": "Test",
        "kid_age": 7,
        "kid_details": "",
        "story_type": "custom",
        "genre": "fantasy",
        "description": "Test",
        "event_id": None,
        "event_data": None,
        "mood": None,
        "length": None,
        "art_style": "digital_fantasy",
        "custom_art_style_prompt": None,
        "story_text": "Test",
        "title": "Test",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": [
            {
                "beat_index": i,
                "beat_name": f"Beat {i}",
                "text_excerpt": f"Text {i}",
                "illustration_prompt": f"Prompt {i}",
                "timestamp_start": 0.0,
                "timestamp_end": 10.0,
                "word_count": 50,
                "image_path": None,
                "image_url": None,
                "generation_metadata": None,
            }
            for i in range(4)
        ],
        "character_description": None,
    }
    
    with patch("app.graph.nodes.illustration_generator.get_illustration_provider", return_value=mock_provider):
        with patch("app.graph.nodes.illustration_generator.save_illustration", return_value="/test/path.png"):
            result = await illustration_generator(state)
    
    scenes = result["scenes"]
    
    # Verify successful images have metadata
    assert scenes[0]["generation_metadata"] is not None
    assert scenes[0]["generation_metadata"]["provider"] == "NanoBanana"
    assert scenes[0]["generation_metadata"]["succeeded"] is True
    
    assert scenes[1]["generation_metadata"] is not None
    assert scenes[1]["generation_metadata"]["succeeded"] is True
    
    # Verify failed images have error metadata
    assert scenes[2]["generation_metadata"] is not None
    assert scenes[2]["generation_metadata"]["succeeded"] is False
    assert "error" in scenes[2]["generation_metadata"]
    
    assert scenes[3]["generation_metadata"] is not None
    assert scenes[3]["generation_metadata"]["succeeded"] is False
