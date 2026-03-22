"""
Tests for Scene Analyzer Node (Stage 3)
TDD: RED tests first, then GREEN implementation
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.graph.state import StoryState, Scene
from app.graph.nodes.scene_analyzer import scene_analyzer


@pytest.mark.asyncio
async def test_scene_analyzer_custom_story():
    """Scene analyzer should detect 8 Story Spine beats for custom stories"""
    # Mock LLM response with valid JSON for 8 beats
    mock_response = {
        "character_description": "7-year-old girl with curly brown hair, green eyes, wearing a yellow dress",
        "scenes": [
            {
                "beat_index": 0,
                "beat_name": "Once upon a time",
                "text_excerpt": "Once upon a time, there was a curious girl named Mia...",
                "illustration_prompt": "A 7-year-old girl with curly brown hair and green eyes wearing a yellow dress stands in a sunny meadow filled with wildflowers, looking curiously at a glowing portal in the distance.",
                "word_count": 45
            },
            {
                "beat_index": 1,
                "beat_name": "Every day",
                "text_excerpt": "Every day, she would visit the same clearing...",
                "illustration_prompt": "The same girl sitting in a forest clearing surrounded by friendly woodland creatures, reading a book under a large oak tree.",
                "word_count": 50
            },
            {
                "beat_index": 2,
                "beat_name": "Until one day",
                "text_excerpt": "Until one day, she discovered a hidden door...",
                "illustration_prompt": "The girl discovering a mysterious glowing door carved into an ancient tree trunk, reaching out to touch it with wonder.",
                "word_count": 48
            },
            {
                "beat_index": 3,
                "beat_name": "Because of that",
                "text_excerpt": "Because of that, she stepped through...",
                "illustration_prompt": "The girl stepping through the magical doorway into a vibrant fantasy realm filled with floating islands and rainbow waterfalls.",
                "word_count": 52
            },
            {
                "beat_index": 4,
                "beat_name": "Because of that",
                "text_excerpt": "Because of that, she met a wise fox...",
                "illustration_prompt": "The girl kneeling beside a majestic silver fox with glowing blue eyes in an enchanted glade, the fox gesturing with its paw toward dark storm clouds in the distance.",
                "word_count": 55
            },
            {
                "beat_index": 5,
                "beat_name": "Because of that",
                "text_excerpt": "Because of that, Mia embarked on a quest...",
                "illustration_prompt": "The girl climbing a steep mountain path carrying a glowing crystal, determination on her face as she approaches a cave entrance wreathed in mystical mist.",
                "word_count": 58
            },
            {
                "beat_index": 6,
                "beat_name": "Until finally",
                "text_excerpt": "Until finally, she gathered all three crystals...",
                "illustration_prompt": "The girl standing before a massive ancient tree, holding three radiant crystals above her head as beams of light shoot into the sky and dispel swirling darkness.",
                "word_count": 60
            },
            {
                "beat_index": 7,
                "beat_name": "And ever since then",
                "text_excerpt": "And ever since then, Mia became the guardian...",
                "illustration_prompt": "The girl sitting peacefully in the now-restored magical realm, wearing a crown of flowers, surrounded by happy creatures as golden sunlight bathes the landscape.",
                "word_count": 52
            }
        ]
    }
    
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(mock_response)))
    
    state: StoryState = {
        "kid_name": "Mia",
        "kid_age": 7,
        "kid_details": "",
        "story_type": "custom",
        "genre": "fantasy",
        "description": "A magical adventure",
        "event_id": None,
        "event_data": None,
        "mood": "exciting",
        "length": "medium",
        "art_style": "watercolor_dream",
        "custom_art_style_prompt": None,
        "story_text": """Once upon a time, there was a curious girl named Mia...""",
        "title": "Mia's Magical Quest",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": None,
        "character_description": None,
    }
    
    with patch("app.graph.nodes.scene_analyzer.get_llm", return_value=mock_llm):
        result = await scene_analyzer(state)
    
    assert "scenes" in result
    assert "character_description" in result
    assert result["scenes"] is not None
    assert len(result["scenes"]) == 8, "Custom stories should have 8 Story Spine beats"
    
    # Verify each scene has required fields
    for i, scene in enumerate(result["scenes"]):
        assert scene["beat_index"] == i
        assert scene["beat_name"], "Each beat should have a name"
        assert scene["text_excerpt"], "Each beat should have text excerpt"
        assert scene["illustration_prompt"], "Each beat should have illustration prompt"
        assert len(scene["illustration_prompt"]) > 50, "Illustration prompt should be detailed"
        assert scene["word_count"] > 0, "Each beat should have word count"
        # New fields added by scene_analyzer
        assert scene["timestamp_start"] == 0.0
        assert scene["timestamp_end"] == 0.0
        assert scene["image_path"] is None
        assert scene["image_url"] is None
    
    # Verify character description
    assert result["character_description"], "Should extract character description"


@pytest.mark.asyncio
async def test_scene_analyzer_historical_story():
    """Scene analyzer should detect 5 narrative beats for historical stories"""
    # Mock LLM response for 5 beats
    mock_response = {
        "character_description": "8-year-old boy with dark hair, brown eyes, wearing modern clothes",
        "scenes": [
            {
                "beat_index": i,
                "beat_name": f"Historical Beat {i}",
                "text_excerpt": f"Historical excerpt {i}",
                "illustration_prompt": f"A detailed historical scene {i} showing the time period with accurate period details and the observer child watching.",
                "word_count": 60
            }
            for i in range(5)
        ]
    }
    
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(mock_response)))
    
    state: StoryState = {
        "kid_name": "Arjun",
        "kid_age": 8,
        "kid_details": "",
        "story_type": "historical",
        "genre": None,
        "description": None,
        "event_id": "moon_landing",
        "event_data": {"name": "Moon Landing", "year": 1969},
        "mood": "exciting",
        "length": "medium",
        "art_style": "vintage_fairy_tale",
        "custom_art_style_prompt": None,
        "story_text": """In a flash of light, Arjun found himself transported...""",
        "title": "Arjun Witnesses the Moon Landing",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": None,
        "character_description": None,
    }
    
    with patch("app.graph.nodes.scene_analyzer.get_llm", return_value=mock_llm):
        result = await scene_analyzer(state)
    
    assert result["scenes"] is not None
    assert len(result["scenes"]) == 5, "Historical stories should have 5 narrative beats"
    
    # Verify structure
    for scene in result["scenes"]:
        assert "beat_index" in scene
        assert "beat_name" in scene
        assert "illustration_prompt" in scene
        assert scene["word_count"] > 0


@pytest.mark.asyncio
async def test_scene_analyzer_skips_when_no_art_style():
    """Scene analyzer should skip when art_style is not set"""
    state: StoryState = {
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
        "art_style": None,  # No art style selected
        "custom_art_style_prompt": None,
        "story_text": "Test story text",
        "title": "Test",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": None,
        "character_description": None,
    }
    
    # No LLM mock needed - should skip before calling LLM
    result = await scene_analyzer(state)
    
    assert result["scenes"] is None, "Should skip when no art style"
    assert result["character_description"] is None


@pytest.mark.asyncio
async def test_scene_analyzer_extracts_character_description():
    """Scene analyzer should extract protagonist's physical description"""
    mock_response = {
        "character_description": "6-year-old girl with wild curly red hair, bright blue eyes, wearing purple backpack and green hiking boots",
        "scenes": [
            {
                "beat_index": i,
                "beat_name": f"Beat {i}",
                "text_excerpt": f"Excerpt {i}",
                "illustration_prompt": f"Detailed prompt {i}",
                "word_count": 40
            }
            for i in range(8)
        ]
    }
    
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(mock_response)))
    
    state: StoryState = {
        "kid_name": "Zara",
        "kid_age": 6,
        "kid_details": "",
        "story_type": "custom",
        "genre": "adventure",
        "description": "A brave explorer",
        "event_id": None,
        "event_data": None,
        "mood": "exciting",
        "length": "short",
        "art_style": "modern_flat",
        "custom_art_style_prompt": None,
        "story_text": """Zara was a brave 6-year-old explorer with wild curly red hair...""",
        "title": "Zara's Crystal Quest",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": None,
        "character_description": None,
    }
    
    with patch("app.graph.nodes.scene_analyzer.get_llm", return_value=mock_llm):
        result = await scene_analyzer(state)
    
    assert result["character_description"], "Should extract character description"
    assert len(result["character_description"]) > 20, "Description should be detailed"


@pytest.mark.asyncio
async def test_scene_analyzer_generates_illustration_prompts():
    """Illustration prompts should be detailed and visual"""
    mock_response = {
        "character_description": "8-year-old boy with short black hair",
        "scenes": [
            {
                "beat_index": i,
                "beat_name": f"Beat {i}",
                "text_excerpt": f"Story excerpt for beat {i}",
                "illustration_prompt": f"A highly detailed visual scene showing an 8-year-old boy with short black hair in a space setting with stars, planets, and spacecraft visible in the background. The boy is {'gazing at stars' if i == 0 else 'piloting a spacecraft' if i == 3 else 'exploring'}.",
                "word_count": 45
            }
            for i in range(8)
        ]
    }
    
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(mock_response)))
    
    state: StoryState = {
        "kid_name": "Leo",
        "kid_age": 8,
        "kid_details": "",
        "story_type": "custom",
        "genre": "space",
        "description": "Space adventure",
        "event_id": None,
        "event_data": None,
        "mood": "exciting",
        "length": "medium",
        "art_style": "digital_fantasy",
        "custom_art_style_prompt": None,
        "story_text": """Leo, an 8-year-old astronaut-in-training...""",
        "title": "Leo's Space Adventure",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": None,
        "character_description": None,
    }
    
    with patch("app.graph.nodes.scene_analyzer.get_llm", return_value=mock_llm):
        result = await scene_analyzer(state)
    
    assert result["scenes"] is not None
    assert len(result["scenes"]) == 8
    
    # Each illustration prompt should be detailed
    for scene in result["scenes"]:
        prompt = scene["illustration_prompt"]
        assert len(prompt) > 50, f"Beat {scene['beat_index']} prompt too short: {prompt}"


@pytest.mark.asyncio
async def test_scene_analyzer_word_count_distribution():
    """Word counts should be provided for each scene"""
    mock_response = {
        "character_description": "Test character",
        "scenes": [
            {
                "beat_index": i,
                "beat_name": f"Beat {i}",
                "text_excerpt": f"Excerpt {i}",
                "illustration_prompt": f"Prompt {i}",
                "word_count": 30 + (i * 5)  # Varying word counts
            }
            for i in range(8)
        ]
    }
    
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(mock_response)))
    
    state: StoryState = {
        "kid_name": "Test",
        "kid_age": 7,
        "kid_details": "",
        "story_type": "custom",
        "genre": "fantasy",
        "description": "Test",
        "event_id": None,
        "event_data": None,
        "mood": None,
        "length": "medium",
        "art_style": "watercolor_dream",
        "custom_art_style_prompt": None,
        "story_text": "Test story with multiple sentences and words to count.",
        "title": "Test Story",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": None,
        "character_description": None,
    }
    
    with patch("app.graph.nodes.scene_analyzer.get_llm", return_value=mock_llm):
        result = await scene_analyzer(state)
    
    assert result["scenes"] is not None
    
    # Verify all scenes have word counts
    for scene in result["scenes"]:
        assert scene["word_count"] > 0, "Each scene should have word count"


@pytest.mark.asyncio
async def test_scene_analyzer_handles_invalid_json():
    """Scene analyzer should handle invalid JSON gracefully"""
    # Mock LLM returning invalid JSON
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="This is not valid JSON {broken"))
    
    state: StoryState = {
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
        "story_text": "Test story",
        "title": "Test",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": None,
        "character_description": None,
    }
    
    with patch("app.graph.nodes.scene_analyzer.get_llm", return_value=mock_llm):
        result = await scene_analyzer(state)
    
    # Should handle error gracefully
    assert "scenes" in result
    assert result["scenes"] is None, "Should return None on JSON parse error"
    assert "error" in result, "Should set error field"


@pytest.mark.asyncio
async def test_scene_analyzer_strips_markdown_code_blocks():
    """Scene analyzer should handle JSON wrapped in markdown code blocks"""
    mock_response_with_markdown = {
        "character_description": "Test character",
        "scenes": [
            {
                "beat_index": i,
                "beat_name": f"Beat {i}",
                "text_excerpt": f"Excerpt {i}",
                "illustration_prompt": f"Detailed prompt for scene {i}",
                "word_count": 40
            }
            for i in range(8)
        ]
    }
    
    # Wrap in markdown code block
    wrapped_content = f"```json\n{json.dumps(mock_response_with_markdown)}\n```"
    
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=wrapped_content))
    
    state: StoryState = {
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
        "story_text": "Test story",
        "title": "Test",
        "segments": [],
        "audio_segments": [],
        "final_audio": b"",
        "duration_seconds": 0,
        "error": None,
        "scenes": None,
        "character_description": None,
    }
    
    with patch("app.graph.nodes.scene_analyzer.get_llm", return_value=mock_llm):
        result = await scene_analyzer(state)
    
    # Should successfully parse despite markdown wrapper
    assert result["scenes"] is not None
    assert len(result["scenes"]) == 8
    assert result["character_description"] == "Test character"
