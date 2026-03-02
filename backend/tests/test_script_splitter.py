import pytest
from app.graph.nodes.script_splitter import script_splitter


@pytest.mark.asyncio
async def test_splits_narrator_and_dialogue():
    state = {
        "story_text": (
            'Once upon a time, Arjun found a magical cave. '
            'Arjun: "Wow, this is amazing!" '
            'A wise old owl sat on a branch. '
            'Owl: "Welcome, young traveler." '
            'Arjun smiled and walked deeper into the cave.'
        ),
        "kid_name": "Arjun",
    }
    result = await script_splitter(state)
    segments = result["segments"]
    assert len(segments) > 0
    narr = [s for s in segments if s["speaker"] == "narrator"]
    dial = [s for s in segments if s["speaker"] != "narrator"]
    assert len(narr) > 0
    assert len(dial) > 0


@pytest.mark.asyncio
async def test_assigns_voice_types():
    state = {
        "story_text": (
            'The king stood tall. '
            'King: "We march at dawn!" '
            'Princess: "I will join you, father." '
            'Arjun: "Can I come too?"'
        ),
        "kid_name": "Arjun",
    }
    result = await script_splitter(state)
    segments = result["segments"]
    voice_types = {s["voice_type"] for s in segments}
    assert "narrator" in voice_types


@pytest.mark.asyncio
async def test_no_dialogue_all_narrator():
    state = {
        "story_text": "Once upon a time there was a beautiful garden. The flowers bloomed every spring.",
        "kid_name": "Arjun",
    }
    result = await script_splitter(state)
    segments = result["segments"]
    assert len(segments) == 1
    assert segments[0]["speaker"] == "narrator"
    assert segments[0]["voice_type"] == "narrator"
