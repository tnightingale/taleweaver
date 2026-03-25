"""
Video transcoder — generates MP4 slideshow from scene illustrations + audio.

Combines scene PNGs with varying durations (from timestamps) and the audio MP3
into an H.264/AAC MP4 suitable for AirPlay to Apple TV.
"""
import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Black placeholder for scenes with missing images
_BLACK_FRAME_CACHE: Path | None = None


def _ensure_black_frame(tmp_dir: Path) -> Path:
    """Create a 1920x1080 black PNG placeholder if needed."""
    global _BLACK_FRAME_CACHE
    if _BLACK_FRAME_CACHE and _BLACK_FRAME_CACHE.exists():
        return _BLACK_FRAME_CACHE

    black_path = tmp_dir / "black.png"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            "color=black:s=1920x1080:d=1",
            "-frames:v", "1",
            black_path,
        ],
        capture_output=True,
        check=True,
    )
    _BLACK_FRAME_CACHE = black_path
    return black_path


def _generate_video_sync(
    story_dir: Path,
    scenes: list[dict],
    audio_path: Path,
    output_path: Path,
) -> Path:
    """
    CPU-bound video generation — runs in a thread pool.

    Uses ffmpeg concat demuxer to combine scene images with per-scene durations,
    then muxes with the audio track.
    """
    concat_path = story_dir / "concat.txt"

    try:
        # Build concat demuxer file
        lines: list[str] = []
        for scene in scenes:
            duration = scene["timestamp_end"] - scene["timestamp_start"]
            if duration <= 0:
                continue

            image_path = scene.get("image_path")
            if image_path and Path(image_path).exists():
                # Paths in concat file must be absolute or relative to the file
                lines.append(f"file '{image_path}'")
            else:
                black = _ensure_black_frame(story_dir)
                lines.append(f"file '{black}'")

            lines.append(f"duration {duration:.3f}")

        if not lines:
            raise ValueError("No scenes with valid durations")

        # ffmpeg concat quirk: repeat last file to avoid it being skipped
        last_file_line = [l for l in lines if l.startswith("file ")][-1]
        lines.append(last_file_line)

        concat_path.write_text("\n".join(lines) + "\n")

        # Run ffmpeg
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_path),
            "-i", str(audio_path),
            "-vf", (
                "scale=1920:1080:force_original_aspect_ratio=decrease,"
                "pad=1920:1080:-1:-1:color=black,"
                "format=yuv420p"
            ),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"ffmpeg stderr: {result.stderr}")
            raise RuntimeError(f"ffmpeg failed (exit {result.returncode}): {result.stderr[-500:]}")

        file_size = output_path.stat().st_size
        logger.info(f"Video generated: {output_path} ({file_size} bytes)")
        return output_path

    finally:
        # Clean up temp concat file
        if concat_path.exists():
            concat_path.unlink()


async def generate_story_video(
    story_dir: Path,
    scenes: list[dict],
    audio_path: Path,
    output_path: Path,
) -> Path:
    """
    Generate an MP4 slideshow video from scene images + audio.

    Args:
        story_dir: Path to /storage/stories/{uuid}/
        scenes: Scene dicts with timestamp_start, timestamp_end, image_path
        audio_path: Path to audio.mp3
        output_path: Path for output video.mp4

    Returns:
        Path to generated video.mp4
    """
    return await asyncio.to_thread(
        _generate_video_sync, story_dir, scenes, audio_path, output_path
    )
