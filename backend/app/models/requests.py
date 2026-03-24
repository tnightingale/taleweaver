from typing import Literal, Optional

from pydantic import BaseModel, Field

VALID_MOODS = Literal["exciting", "heartwarming", "funny", "mysterious"]
VALID_LENGTHS = Literal["short", "medium", "long"]


class KidProfile(BaseModel):
    name: str = Field(max_length=50)
    age: int = Field(ge=3, le=12)
    favorite_animal: Optional[str] = Field(default=None, max_length=50)
    favorite_color: Optional[str] = Field(default=None, max_length=50)
    hobby: Optional[str] = Field(default=None, max_length=100)
    best_friend: Optional[str] = Field(default=None, max_length=50)
    pet_name: Optional[str] = Field(default=None, max_length=50)
    personality: Optional[str] = Field(default=None, max_length=50)


class CustomStoryRequest(BaseModel):
    kid: KidProfile
    genre: str = Field(max_length=50)
    description: str = Field(max_length=500)
    mood: Optional[VALID_MOODS] = None
    length: Optional[VALID_LENGTHS] = None
    art_style: Optional[str] = Field(default=None, max_length=50)  # Art style preset ID
    custom_art_style_prompt: Optional[str] = Field(default=None, max_length=500)  # Custom style prompt


class HistoricalStoryRequest(BaseModel):
    kid: KidProfile
    event_id: str = Field(max_length=100)
    mood: Optional[VALID_MOODS] = None
    length: Optional[VALID_LENGTHS] = None
    art_style: Optional[str] = Field(default=None, max_length=50)  # Art style preset ID
    custom_art_style_prompt: Optional[str] = Field(default=None, max_length=500)  # Custom style prompt


class UpdateStoryTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class RegenerateIllustrationsRequest(BaseModel):
    mode: str = Field(default="missing")  # "missing" | "all" | "add" | "single"
    art_style: Optional[str] = Field(default=None, max_length=50)
    custom_art_style_prompt: Optional[str] = Field(default=None, max_length=500)
    scene_index: Optional[int] = None
