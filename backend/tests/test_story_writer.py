import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.graph.nodes.story_writer import story_writer


@pytest.mark.asyncio
async def test_story_writer_custom():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content='TITLE: Arjun and the Magic Tiger\nSTORY:\nOnce upon a time, Arjun found a glowing paintbrush.'
    ))

    with patch("app.graph.nodes.story_writer.get_llm", return_value=mock_llm):
        state = {
            "kid_name": "Arjun",
            "kid_age": 7,
            "kid_details": "loves tigers",
            "story_type": "custom",
            "genre": "fantasy",
            "description": "A magical paintbrush",
            "event_id": None,
            "event_data": None,
        }
        result = await story_writer(state)
        assert "story_text" in result
        assert "title" in result
        assert result["title"] == "Arjun and the Magic Tiger"
        assert "paintbrush" in result["story_text"]


@pytest.mark.asyncio
async def test_story_writer_historical():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
        content='TITLE: Arjun Witnesses the Great Escape\nSTORY:\nArjun blinked and found himself in Agra.'
    ))

    with patch("app.graph.nodes.story_writer.get_llm", return_value=mock_llm):
        state = {
            "kid_name": "Arjun",
            "kid_age": 7,
            "kid_details": "",
            "story_type": "historical",
            "genre": None,
            "description": None,
            "event_id": "shivaji-agra-escape",
            "event_data": {
                "title": "Shivaji's Escape",
                "figure": "Shivaji Maharaj",
                "year": 1666,
                "key_facts": ["Escaped in fruit baskets"]
            },
        }
        result = await story_writer(state)
        assert result["title"] == "Arjun Witnesses the Great Escape"
        assert "Agra" in result["story_text"]
