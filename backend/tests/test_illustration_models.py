"""
Tests for Illustration Feature - Database Schema & Models (Stage 1)
Tests verify that the illustration fields are properly added to database models
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import json

from app.db.crud import save_story, get_story_by_id
from app.db.database import get_db, init_db, SessionLocal
from app.db.models import Story
from app.graph.state import Scene, StoryState
from app.models.responses import SceneResponse, JobCompleteResponse, StoryResponse
from app.models.requests import CustomStoryRequest, HistoricalStoryRequest, KidProfile


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    test_dir = Path(tempfile.mkdtemp())
    test_db_path = test_dir / "test.db"
    
    # Override database URL
    import app.db.database as db_module
    original_url = db_module.SQLALCHEMY_DATABASE_URL
    db_module.SQLALCHEMY_DATABASE_URL = f"sqlite:///{test_db_path}"
    
    # Recreate engine and session
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    db_module.engine = create_engine(
        db_module.SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_module.engine)
    
    # Initialize tables
    init_db()
    
    yield db_module.SessionLocal()
    
    # Cleanup
    db_module.SQLALCHEMY_DATABASE_URL = original_url
    shutil.rmtree(test_dir)


def test_story_model_has_illustration_columns(test_db):
    """Story model should have art_style, has_illustrations, and scene_data columns"""
    # Create a story instance
    story = Story(
        id="test-123",
        short_id="abc12345",
        title="Test Story",
        kid_name="Test Kid",
        kid_age=7,
        story_type="custom",
        transcript="Test transcript",
        duration_seconds=120,
        audio_path="/test/path.mp3",
        art_style="watercolor_dream",
        has_illustrations=True,
        scene_data={"test": "data"}
    )
    
    test_db.add(story)
    test_db.commit()
    
    # Retrieve and verify
    retrieved = test_db.query(Story).filter_by(id="test-123").first()
    assert retrieved.art_style == "watercolor_dream"
    assert retrieved.has_illustrations is True
    assert retrieved.scene_data == {"test": "data"}


def test_story_model_illustration_fields_nullable(test_db):
    """Illustration fields should be nullable for backward compatibility"""
    # Create a story without illustration fields
    story = Story(
        id="test-456",
        short_id="def67890",
        title="Test Story Without Illustrations",
        kid_name="Test Kid",
        kid_age=7,
        story_type="custom",
        transcript="Test transcript",
        duration_seconds=120,
        audio_path="/test/path.mp3"
        # No illustration fields provided
    )
    
    test_db.add(story)
    test_db.commit()
    
    # Retrieve and verify
    retrieved = test_db.query(Story).filter_by(id="test-456").first()
    assert retrieved.art_style is None
    assert retrieved.has_illustrations is False  # Should default to False
    assert retrieved.scene_data is None


def test_story_model_with_scene_data_json(test_db):
    """Story model should correctly store and retrieve scene_data JSON"""
    scene_data = {
        "scenes": [
            {
                "beat_index": 0,
                "beat_name": "Once upon a time",
                "text_excerpt": "Test excerpt",
                "illustration_prompt": "A test scene",
                "timestamp_start": 0.0,
                "timestamp_end": 15.5,
                "word_count": 45,
                "image_path": "/storage/stories/test-789/scene_0.png",
                "image_url": "/api/illustrations/test-789/scene_0.png",
                "generation_metadata": {
                    "provider": "nanobanana2",
                    "reference_image": None
                }
            },
            {
                "beat_index": 1,
                "beat_name": "Every day",
                "text_excerpt": "Another excerpt",
                "illustration_prompt": "Another test scene",
                "timestamp_start": 15.5,
                "timestamp_end": 30.0,
                "word_count": 50,
                "image_path": "/storage/stories/test-789/scene_1.png",
                "image_url": "/api/illustrations/test-789/scene_1.png",
                "generation_metadata": {
                    "provider": "nanobanana2",
                    "reference_image": "/api/illustrations/test-789/scene_0.png"
                }
            }
        ],
        "art_style_prompt": "soft watercolor painting, children's book",
        "character_description": "7-year-old boy, brown hair, blue eyes"
    }
    
    story = Story(
        id="test-789",
        short_id="ghi12345",
        title="Story with Scene Data",
        kid_name="Test Kid",
        kid_age=7,
        story_type="custom",
        transcript="Full transcript",
        duration_seconds=120,
        audio_path="/test/path.mp3",
        art_style="watercolor_dream",
        has_illustrations=True,
        scene_data=scene_data
    )
    
    test_db.add(story)
    test_db.commit()
    
    # Retrieve and verify JSON structure preserved
    retrieved = test_db.query(Story).filter_by(id="test-789").first()
    assert retrieved.scene_data is not None
    assert "scenes" in retrieved.scene_data
    assert len(retrieved.scene_data["scenes"]) == 2
    assert retrieved.scene_data["scenes"][0]["beat_name"] == "Once upon a time"
    assert retrieved.scene_data["scenes"][1]["beat_name"] == "Every day"
    assert retrieved.scene_data["character_description"] == "7-year-old boy, brown hair, blue eyes"


def test_scene_typeddict_structure():
    """Scene TypedDict should have all required fields"""
    scene: Scene = {
        "beat_index": 0,
        "beat_name": "Once upon a time",
        "text_excerpt": "Test excerpt",
        "illustration_prompt": "A visual scene description",
        "timestamp_start": 0.0,
        "timestamp_end": 15.0,
        "word_count": 45,
        "image_path": "/storage/test.png",
        "image_url": "/api/test.png",
        "generation_metadata": {"provider": "nanobanana2"}
    }
    
    # Verify all required fields present
    assert scene["beat_index"] == 0
    assert scene["beat_name"] == "Once upon a time"
    assert scene["text_excerpt"] == "Test excerpt"
    assert scene["illustration_prompt"] == "A visual scene description"
    assert scene["timestamp_start"] == 0.0
    assert scene["timestamp_end"] == 15.0
    assert scene["word_count"] == 45
    assert scene["image_path"] == "/storage/test.png"
    assert scene["image_url"] == "/api/test.png"
    assert scene["generation_metadata"] == {"provider": "nanobanana2"}


def test_custom_story_request_accepts_art_style():
    """CustomStoryRequest should accept art_style and custom_art_style_prompt"""
    kid = KidProfile(name="Test Kid", age=7)
    
    # Test with art_style preset
    request = CustomStoryRequest(
        kid=kid,
        genre="fantasy",
        description="A magical adventure",
        mood="exciting",
        length="medium",
        art_style="watercolor_dream"
    )
    
    assert request.art_style == "watercolor_dream"
    assert request.custom_art_style_prompt is None
    
    # Test with custom art style prompt
    request_custom = CustomStoryRequest(
        kid=kid,
        genre="fantasy",
        description="A magical adventure",
        art_style="custom",
        custom_art_style_prompt="oil painting, impressionist style"
    )
    
    assert request_custom.art_style == "custom"
    assert request_custom.custom_art_style_prompt == "oil painting, impressionist style"


def test_historical_story_request_accepts_art_style():
    """HistoricalStoryRequest should accept art_style and custom_art_style_prompt"""
    kid = KidProfile(name="Test Kid", age=7)
    
    request = HistoricalStoryRequest(
        kid=kid,
        event_id="moon_landing",
        mood="exciting",
        art_style="vintage_fairy_tale"
    )
    
    assert request.art_style == "vintage_fairy_tale"
    assert request.custom_art_style_prompt is None


def test_scene_response_model_serialization():
    """SceneResponse should correctly serialize scene data"""
    scene = SceneResponse(
        beat_index=0,
        beat_name="Once upon a time",
        text_excerpt="Test excerpt",
        timestamp_start=0.0,
        timestamp_end=15.5,
        image_url="/api/illustrations/test.png"
    )
    
    # Test serialization
    data = scene.model_dump()
    assert data["beat_index"] == 0
    assert data["beat_name"] == "Once upon a time"
    assert data["text_excerpt"] == "Test excerpt"
    assert data["timestamp_start"] == 0.0
    assert data["timestamp_end"] == 15.5
    assert data["image_url"] == "/api/illustrations/test.png"


def test_job_complete_response_includes_illustration_fields():
    """JobCompleteResponse should include has_illustrations, art_style, and scenes"""
    scenes = [
        SceneResponse(
            beat_index=0,
            beat_name="Once upon a time",
            text_excerpt="Test",
            timestamp_start=0.0,
            timestamp_end=10.0,
            image_url="/test.png"
        )
    ]
    
    response = JobCompleteResponse(
        job_id="test-123",
        status="complete",
        title="Test Story",
        duration_seconds=120,
        audio_url="/audio/test.mp3",
        transcript="Full transcript",
        short_id="abc12345",
        permalink="/s/abc12345",
        has_illustrations=True,
        art_style="watercolor_dream",
        scenes=scenes
    )
    
    assert response.has_illustrations is True
    assert response.art_style == "watercolor_dream"
    assert len(response.scenes) == 1
    assert response.scenes[0].beat_name == "Once upon a time"


def test_story_response_includes_illustration_fields():
    """StoryResponse should include has_illustrations, art_style, and scenes"""
    scenes = [
        SceneResponse(
            beat_index=0,
            beat_name="Once upon a time",
            text_excerpt="Test",
            timestamp_start=0.0,
            timestamp_end=10.0,
            image_url="/test.png"
        )
    ]
    
    response = StoryResponse(
        id="test-123",
        short_id="abc12345",
        title="Test Story",
        kid_name="Test Kid",
        kid_age=7,
        story_type="custom",
        genre="fantasy",
        transcript="Full transcript",
        duration_seconds=120,
        created_at="2026-03-21T10:00:00",
        permalink="/s/abc12345",
        audio_url="/audio/test.mp3",
        has_illustrations=True,
        art_style="watercolor_dream",
        scenes=scenes
    )
    
    assert response.has_illustrations is True
    assert response.art_style == "watercolor_dream"
    assert len(response.scenes) == 1
