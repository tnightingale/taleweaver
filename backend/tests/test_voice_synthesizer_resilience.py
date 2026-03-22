"""
Tests for Voice Synthesizer Resilience (TDD RED Phase)
Testing incremental saves, retry logic, and quota handling
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from app.graph.state import StoryState
from app.graph.nodes.voice_synthesizer import voice_synthesizer, QuotaExceededError, RateLimitError


@pytest.mark.asyncio
async def test_voice_synthesizer_saves_segments_incrementally(test_db):
    """Should save each segment to temp storage as it's synthesized"""
    # Mock ElevenLabs to return fake audio
    fake_audio = b"fake-mp3-data"
    
    with patch("app.graph.nodes.voice_synthesizer._synthesize_segment", return_value=fake_audio):
        with patch("app.graph.nodes.voice_synthesizer.save_temp_audio_segment") as mock_save:
            state: StoryState = {
                "job_id": "test-incremental",
                "kid_name": "Test",
                "kid_age": 7,
                "kid_details": "",
                "story_type": "custom",
                "genre": None,
                "description": None,
                "event_id": None,
                "event_data": None,
                "mood": None,
                "length": None,
                "art_style": None,
                "custom_art_style_prompt": None,
                "story_text": "",
                "title": "",
                "segments": [
                    {"speaker": "Narrator", "voice_type": "narrator", "text": "Segment 1"},
                    {"speaker": "Narrator", "voice_type": "narrator", "text": "Segment 2"},
                    {"speaker": "Character", "voice_type": "male", "text": "Segment 3"},
                ],
                "audio_segments": [],
                "final_audio": b"",
                "duration_seconds": 0,
                "error": None,
                "scenes": None,
                "character_description": None,
            }
            
            result = await voice_synthesizer(state)
            
            # Verify all segments synthesized
            assert len(result["audio_segments"]) == 3
            
            # Verify each segment was saved to temp storage
            assert mock_save.call_count == 3
            mock_save.assert_any_call("test-incremental", 0, fake_audio)
            mock_save.assert_any_call("test-incremental", 1, fake_audio)
            mock_save.assert_any_call("test-incremental", 2, fake_audio)


@pytest.mark.asyncio
async def test_voice_synthesizer_quota_error_preserves_partial(test_db):
    """Should preserve partial segments when quota is exceeded"""
    call_count = [0]
    fake_audio = b"fake-mp3"
    
    def mock_synthesize(client, voice_id, text):
        call_count[0] += 1
        if call_count[0] > 3:  # Fail after 3 segments
            raise Exception("quota_exceeded: ElevenLabs quota limit reached")
        return fake_audio
    
    with patch("app.graph.nodes.voice_synthesizer._synthesize_segment", side_effect=mock_synthesize):
        with patch("app.graph.nodes.voice_synthesizer.save_temp_audio_segment"):
            state: StoryState = {
                "job_id": "test-quota",
                "kid_name": "Test",
                "kid_age": 7,
                "kid_details": "",
                "story_type": "custom",
                "genre": None,
                "description": None,
                "event_id": None,
                "event_data": None,
                "mood": None,
                "length": None,
                "art_style": None,
                "custom_art_style_prompt": None,
                "story_text": "",
                "title": "",
                "segments": [
                    {"speaker": "Narrator", "voice_type": "narrator", "text": f"Segment {i}"}
                    for i in range(6)
                ],
                "audio_segments": [],
                "final_audio": b"",
                "duration_seconds": 0,
                "error": None,
                "scenes": None,
                "character_description": None,
            }
            
            result = await voice_synthesizer(state)
            
            # Should have partial results
            assert len(result["audio_segments"]) == 3, "Should preserve 3 segments before quota error"
            assert result.get("partial_completion") == 3, "Should indicate stopped at index 3"
            assert result.get("resumable") is True, "Quota errors should be resumable"
            assert "quota" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_voice_synthesizer_resumes_from_checkpoint(test_db):
    """Should resume from previously saved segments"""
    fake_audio = b"fake-mp3"
    
    # Mock loading 3 existing segments
    existing_segments = [b"segment-0", b"segment-1", b"segment-2"]
    
    with patch("app.graph.nodes.voice_synthesizer.load_temp_audio_segments", return_value=existing_segments):
        with patch("app.graph.nodes.voice_synthesizer._synthesize_segment", return_value=fake_audio):
            with patch("app.graph.nodes.voice_synthesizer.save_temp_audio_segment"):
                state: StoryState = {
                    "job_id": "test-resume",
                    "kid_name": "Test",
                    "kid_age": 7,
                    "kid_details": "",
                    "story_type": "custom",
                    "genre": None,
                    "description": None,
                    "event_id": None,
                    "event_data": None,
                    "mood": None,
                    "length": None,
                    "art_style": None,
                    "custom_art_style_prompt": None,
                    "story_text": "",
                    "title": "",
                    "segments": [
                        {"speaker": "Narrator", "voice_type": "narrator", "text": f"Segment {i}"}
                        for i in range(6)  # Total 6 segments
                    ],
                    "audio_segments": [],
                    "final_audio": b"",
                    "duration_seconds": 0,
                    "error": None,
                    "scenes": None,
                    "character_description": None,
                }
                
                result = await voice_synthesizer(state)
                
                # Should have all 6 segments (3 loaded + 3 new)
                assert len(result["audio_segments"]) == 6
                # First 3 should be from checkpoint
                assert result["audio_segments"][0] == b"segment-0"
                assert result["audio_segments"][1] == b"segment-1"
                assert result["audio_segments"][2] == b"segment-2"
                # Last 3 should be newly synthesized
                assert result["audio_segments"][3] == fake_audio
                assert result["audio_segments"][4] == fake_audio
                assert result["audio_segments"][5] == fake_audio


@pytest.mark.asyncio
async def test_voice_synthesizer_retries_transient_errors():
    """Should retry transient errors with exponential backoff"""
    call_count = [0]
    fake_audio = b"fake-mp3"
    
    def mock_synthesize_with_transient_error(client, voice_id, text):
        call_count[0] += 1
        if call_count[0] <= 2:  # Fail first 2 attempts
            raise Exception("503 Service Temporarily Unavailable")
        return fake_audio  # Succeed on 3rd attempt
    
    with patch("app.graph.nodes.voice_synthesizer._synthesize_segment", side_effect=mock_synthesize_with_transient_error):
        with patch("app.graph.nodes.voice_synthesizer.save_temp_audio_segment"):
            state: StoryState = {
                "job_id": "test-retry",
                "kid_name": "Test",
                "kid_age": 7,
                "kid_details": "",
                "story_type": "custom",
                "genre": None,
                "description": None,
                "event_id": None,
                "event_data": None,
                "mood": None,
                "length": None,
                "art_style": None,
                "custom_art_style_prompt": None,
                "story_text": "",
                "title": "",
                "segments": [
                    {"speaker": "Narrator", "voice_type": "narrator", "text": "Test segment"}
                ],
                "audio_segments": [],
                "final_audio": b"",
                "duration_seconds": 0,
                "error": None,
                "scenes": None,
                "character_description": None,
            }
            
            result = await voice_synthesizer(state)
            
            # Should succeed after retries
            assert len(result["audio_segments"]) == 1
            assert call_count[0] == 3, "Should have retried 3 times total"


@pytest.mark.asyncio
async def test_voice_synthesizer_distinguishes_quota_vs_rate_limit():
    """Should handle quota errors differently from rate limits"""
    # Test quota error (not retryable immediately)
    def mock_quota_error(client, voice_id, text):
        raise Exception("quota_exceeded: Monthly character limit reached")
    
    with patch("app.graph.nodes.voice_synthesizer._synthesize_segment", side_effect=mock_quota_error):
        with patch("app.graph.nodes.voice_synthesizer.save_temp_audio_segment"):
            state: StoryState = {
                "job_id": "test-quota-classify",
                "kid_name": "Test",
                "kid_age": 7,
                "kid_details": "",
                "story_type": "custom",
                "genre": None,
                "description": None,
                "event_id": None,
                "event_data": None,
                "mood": None,
                "length": None,
                "art_style": None,
                "custom_art_style_prompt": None,
                "story_text": "",
                "title": "",
                "segments": [
                    {"speaker": "Narrator", "voice_type": "narrator", "text": "Test"}
                ],
                "audio_segments": [],
                "final_audio": b"",
                "duration_seconds": 0,
                "error": None,
                "scenes": None,
                "character_description": None,
            }
            
            result = await voice_synthesizer(state)
            
            # Should identify as quota error
            assert result.get("resumable") is True
            assert "quota" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_voice_synthesizer_updates_job_progress(test_db):
    """Should update job progress after each segment"""
    from app.db.crud import create_job_state, get_job_state
    
    # Create job in database
    create_job_state(test_db, "test-progress", ["synthesizing"])
    
    fake_audio = b"fake-mp3"
    
    with patch("app.graph.nodes.voice_synthesizer._synthesize_segment", return_value=fake_audio):
        with patch("app.graph.nodes.voice_synthesizer.save_temp_audio_segment"):
            state: StoryState = {
                "job_id": "test-progress",
                "kid_name": "Test",
                "kid_age": 7,
                "kid_details": "",
                "story_type": "custom",
                "genre": None,
                "description": None,
                "event_id": None,
                "event_data": None,
                "mood": None,
                "length": None,
                "art_style": None,
                "custom_art_style_prompt": None,
                "story_text": "",
                "title": "",
                "segments": [
                    {"speaker": "Narrator", "voice_type": "narrator", "text": f"Segment {i}"}
                    for i in range(5)
                ],
                "audio_segments": [],
                "final_audio": b"",
                "duration_seconds": 0,
                "error": None,
                "scenes": None,
                "character_description": None,
            }
            
            result = await voice_synthesizer(state)
            
            # Check that job progress was updated
            job = get_job_state(test_db, "test-progress")
            # Progress should reflect completion (or at least > 0)
            # This will be implemented in the GREEN phase
            assert len(result["audio_segments"]) == 5
