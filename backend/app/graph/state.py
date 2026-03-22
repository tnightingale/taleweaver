from typing import Optional
from typing_extensions import TypedDict


class Segment(TypedDict):
    speaker: str
    voice_type: str  # "narrator", "male", "female", "child"
    text: str


class Scene(TypedDict):
    """Scene metadata for illustration generation"""
    beat_index: int
    beat_name: str
    text_excerpt: str
    illustration_prompt: str
    timestamp_start: float
    timestamp_end: float
    word_count: int
    image_path: Optional[str]
    image_url: Optional[str]
    generation_metadata: Optional[dict]


class StoryState(TypedDict):
    # Input
    kid_name: str
    kid_age: int
    kid_details: str  # Formatted optional details
    story_type: str  # "custom" or "historical"
    genre: Optional[str]
    description: Optional[str]
    event_id: Optional[str]
    event_data: Optional[dict]
    mood: Optional[str]
    length: Optional[str]
    
    # Illustration inputs
    art_style: Optional[str]  # Art style preset ID or "custom"
    custom_art_style_prompt: Optional[str]  # User's custom prompt if art_style="custom"

    # Pipeline outputs
    story_text: str
    title: str
    segments: list[Segment]
    audio_segments: list[bytes]
    final_audio: bytes
    duration_seconds: int
    error: Optional[str]
    
    # Illustration outputs
    scenes: Optional[list[Scene]]  # Scene metadata with illustration data
    character_description: Optional[str]  # Extracted character description for consistency
