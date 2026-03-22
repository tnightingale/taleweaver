from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str
    stages: list[str]
    current_stage: str


class PartialProgress(BaseModel):
    """Partial completion details for failed jobs"""
    segments_completed: Optional[int] = None
    segments_total: Optional[int] = None
    illustrations_completed: Optional[int] = None
    illustrations_total: Optional[int] = None
    checkpoint_node: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    current_stage: str
    progress: int = 0
    total_segments: int = 0
    error: str = ""
    resumable: bool = False
    partial_progress: Optional[PartialProgress] = None
    retry_count: int = 0


class SceneResponse(BaseModel):
    """Scene metadata with illustration information"""
    beat_index: int
    beat_name: str
    text_excerpt: str
    timestamp_start: float
    timestamp_end: float
    image_url: Optional[str] = None


class JobCompleteResponse(BaseModel):
    job_id: str
    status: str
    title: str
    duration_seconds: int
    audio_url: str
    transcript: str = ""
    short_id: str = ""
    permalink: str = ""
    has_illustrations: bool = False
    art_style: Optional[str] = None
    scenes: Optional[List[SceneResponse]] = None


class StoryResponse(BaseModel):
    """Response model for permalink story retrieval"""
    id: str
    short_id: str
    title: str
    kid_name: str
    kid_age: int
    story_type: str
    genre: Optional[str] = None
    event_id: Optional[str] = None
    transcript: str
    duration_seconds: int
    created_at: str
    permalink: str
    audio_url: str
    has_illustrations: bool = False
    art_style: Optional[str] = None
    scenes: Optional[List[SceneResponse]] = None


class StoriesListResponse(BaseModel):
    """Response model for library story listing"""
    stories: list[StoryResponse]
    total: int
    has_more: bool
