from pydantic import BaseModel
from typing import Optional


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str
    stages: list[str]
    current_stage: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    current_stage: str
    progress: int = 0
    total_segments: int = 0
    error: str = ""


class JobCompleteResponse(BaseModel):
    job_id: str
    status: str
    title: str
    duration_seconds: int
    audio_url: str
    transcript: str = ""
    short_id: str = ""
    permalink: str = ""


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
