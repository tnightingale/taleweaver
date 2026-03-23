"""
Tests that I/O-heavy and CPU-bound pipeline nodes do NOT block the asyncio event loop.

The key invariant: while a pipeline node is doing heavy work (audio stitching,
file writes), other coroutines on the same event loop must still be able to run.
If the event loop is blocked, concurrent tasks will starve.
"""
import asyncio
import io
import pytest
from pydub.generators import Sine


def _make_test_audio(duration_ms: int = 500) -> bytes:
    """Generate a short sine wave as MP3 bytes."""
    tone = Sine(440).to_audio_segment(duration=duration_ms)
    buf = io.BytesIO()
    tone.export(buf, format="mp3")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_audio_stitcher_does_not_block_event_loop():
    """
    Verify that audio_stitcher yields control to the event loop during processing.

    Strategy: run audio_stitcher concurrently with a "canary" coroutine that
    increments a counter every 50ms. If the event loop is blocked, the canary
    won't run and the counter will be 0.
    """
    from app.graph.nodes.audio_stitcher import audio_stitcher

    # Create enough audio segments to make stitching take noticeable time
    segments = [_make_test_audio(1000) for _ in range(5)]
    state = {"audio_segments": segments}

    canary_ticks = 0
    canary_running = True

    async def canary():
        nonlocal canary_ticks
        while canary_running:
            await asyncio.sleep(0.05)
            canary_ticks += 1

    canary_task = asyncio.create_task(canary())
    result = await audio_stitcher(state)
    canary_running = False
    await canary_task

    # The stitcher should have produced valid output
    assert "final_audio" in result
    assert result["duration_seconds"] > 0

    # The canary MUST have ticked at least once, proving the event loop wasn't blocked
    assert canary_ticks > 0, (
        "Event loop was blocked during audio_stitcher — canary coroutine never ran. "
        "audio_stitcher must use asyncio.to_thread() for CPU-bound pydub operations."
    )


@pytest.mark.asyncio
async def test_audio_stitcher_with_background_music_does_not_block():
    """Same test but with mood/background music processing included."""
    from app.graph.nodes.audio_stitcher import audio_stitcher

    segments = [_make_test_audio(800) for _ in range(4)]
    state = {"audio_segments": segments, "mood": "exciting"}

    canary_ticks = 0
    canary_running = True

    async def canary():
        nonlocal canary_ticks
        while canary_running:
            await asyncio.sleep(0.05)
            canary_ticks += 1

    canary_task = asyncio.create_task(canary())
    result = await audio_stitcher(state)
    canary_running = False
    await canary_task

    assert "final_audio" in result
    assert canary_ticks > 0, (
        "Event loop was blocked during audio_stitcher with background music. "
        "All pydub operations must run in a thread pool."
    )
