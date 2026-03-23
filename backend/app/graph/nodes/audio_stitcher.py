import asyncio
import io
import logging
from pathlib import Path
from typing import Optional, List

from pydub import AudioSegment

from app.config import settings
from app.graph.state import StoryState

logger = logging.getLogger(__name__)

PAUSE_MS = 500  # Half-second pause between segments
MUSIC_DIR = settings.music_path
MUSIC_VOLUME_DB = -18


def _load_background_music(mood: Optional[str], target_duration_ms: int) -> Optional[AudioSegment]:
    """Load and loop background music to match story duration."""
    mood_key = mood if mood in ("exciting", "heartwarming", "funny", "mysterious") else "default"
    music_path = MUSIC_DIR / f"{mood_key}.mp3"

    if not music_path.exists():
        logger.warning(f"Background music not found: {music_path}")
        return None

    music = AudioSegment.from_mp3(str(music_path))
    loops_needed = (target_duration_ms // len(music)) + 1
    looped = music * loops_needed
    trimmed = looped[:target_duration_ms]
    trimmed = trimmed.fade_in(2000).fade_out(3000)
    logger.info(f"Background music: mood={mood_key}, loops={loops_needed}, duration={target_duration_ms}ms")
    return trimmed + MUSIC_VOLUME_DB


def _stitch_sync(audio_segments: List[bytes], mood: Optional[str], output_path: Optional[Path] = None) -> dict:
    """
    CPU-bound audio stitching — runs in a thread pool, never on the event loop.

    Combines audio segments with pauses, overlays background music, and exports
    directly to disk (if output_path given) to avoid holding the final MP3 in memory.
    """
    pause = AudioSegment.silent(duration=PAUSE_MS)
    combined = AudioSegment.empty()

    for i, audio_bytes in enumerate(audio_segments):
        segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
        combined += segment
        if i < len(audio_segments) - 1:
            combined += pause

    logger.info(f"Stitched {len(audio_segments)} segments, narration duration={len(combined)}ms")

    bg_music = _load_background_music(mood, len(combined))
    if bg_music is not None:
        combined = combined.overlay(bg_music)

    duration_seconds = int(len(combined) / 1000)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.export(str(output_path), format="mp3")
        file_size = output_path.stat().st_size
        logger.info(f"Final audio written to disk: {output_path}, duration={duration_seconds}s, size={file_size} bytes")
        return {"final_audio_path": str(output_path), "duration_seconds": duration_seconds}
    else:
        # Fallback: return bytes in memory (for tests without storage)
        buf = io.BytesIO()
        combined.export(buf, format="mp3")
        final_bytes = buf.getvalue()
        logger.info(f"Final audio: duration={duration_seconds}s, size={len(final_bytes)} bytes")
        return {"final_audio": final_bytes, "duration_seconds": duration_seconds}


async def audio_stitcher(state: StoryState) -> dict:
    audio_segments = state["audio_segments"]
    mood = state.get("mood")

    # Write directly to disk when we have a job_id (production pipeline)
    output_path = None
    job_id = state.get("job_id")
    if job_id:
        output_path = settings.storage_path / "stories" / job_id / "audio.mp3"

    return await asyncio.to_thread(_stitch_sync, audio_segments, mood, output_path)
