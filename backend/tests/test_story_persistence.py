"""
TDD Tests for Story Persistence (Database Layer)
RED Phase: These tests should FAIL initially
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from app.db.crud import save_story, get_story_by_id, get_story_by_short_id, generate_short_id
from app.db.database import get_db, init_db, SessionLocal
from app.db.models import Story


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    # Create temp directory for test database
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


def test_generate_short_id_creates_8_char_string():
    """Short ID should be exactly 8 characters"""
    short_id = generate_short_id()
    assert len(short_id) == 8


def test_generate_short_id_uses_alphanumeric_lowercase():
    """Short ID should only contain a-z and 0-9"""
    short_id = generate_short_id()
    assert short_id.isalnum()
    assert short_id.islower()


def test_generate_short_id_is_unique():
    """Multiple calls should generate different IDs"""
    ids = [generate_short_id() for _ in range(100)]
    assert len(set(ids)) == 100, "Generated duplicate IDs"


def test_save_story_creates_database_record(test_db, tmp_path):
    """Saving a story creates a database entry"""
    # Override storage path for testing
    import app.config as config_module
    original_storage = config_module.settings.storage_path
    config_module.settings.storage_path = tmp_path
    
    try:
        story_id = "test-uuid-123"
        audio_bytes = b"fake audio data"
        
        story = save_story(
            db=test_db,
            story_id=story_id,
            title="Test Story",
            kid_name="Arjun",
            kid_age=7,
            story_type="custom",
            transcript="Once upon a time...",
            duration_seconds=180,
            audio_bytes=audio_bytes,
            genre="fantasy",
            mood="exciting",
            length="medium",
        )
        
        assert story.id == story_id
        assert story.title == "Test Story"
        assert story.kid_name == "Arjun"
        assert story.kid_age == 7
        assert story.story_type == "custom"
        assert story.genre == "fantasy"
        assert story.short_id is not None
        assert len(story.short_id) == 8
    finally:
        config_module.settings.storage_path = original_storage


def test_save_story_creates_audio_file(test_db, tmp_path):
    """Saving a story writes audio to filesystem"""
    import app.config as config_module
    original_storage = config_module.settings.storage_path
    config_module.settings.storage_path = tmp_path
    
    try:
        story_id = "test-uuid-456"
        audio_bytes = b"test audio content"
        
        story = save_story(
            db=test_db,
            story_id=story_id,
            title="Audio Test",
            kid_name="Maya",
            kid_age=5,
            story_type="historical",
            transcript="Historical story...",
            duration_seconds=120,
            audio_bytes=audio_bytes,
            event_id="test-event",
        )
        
        audio_path = Path(story.audio_path)
        assert audio_path.exists()
        assert audio_path.read_bytes() == audio_bytes
    finally:
        config_module.settings.storage_path = original_storage


def test_get_story_by_id_returns_story(test_db, tmp_path):
    """Can retrieve story by UUID"""
    import app.config as config_module
    original_storage = config_module.settings.storage_path
    config_module.settings.storage_path = tmp_path
    
    try:
        story_id = "retrieve-test-789"
        saved_story = save_story(
            db=test_db,
            story_id=story_id,
            title="Retrieve Test",
            kid_name="Liam",
            kid_age=9,
            story_type="custom",
            transcript="Test transcript",
            duration_seconds=150,
            audio_bytes=b"audio",
            genre="adventure",
        )
        
        retrieved = get_story_by_id(test_db, story_id)
        assert retrieved is not None
        assert retrieved.id == story_id
        assert retrieved.title == "Retrieve Test"
        assert retrieved.short_id == saved_story.short_id
    finally:
        config_module.settings.storage_path = original_storage


def test_get_story_by_id_not_found_returns_none(test_db):
    """Returns None for non-existent story ID"""
    result = get_story_by_id(test_db, "nonexistent-id")
    assert result is None


def test_get_story_by_short_id_returns_story(test_db, tmp_path):
    """Can retrieve story using compact short ID"""
    import app.config as config_module
    original_storage = config_module.settings.storage_path
    config_module.settings.storage_path = tmp_path
    
    try:
        saved_story = save_story(
            db=test_db,
            story_id="shortid-test-999",
            title="Short ID Test",
            kid_name="Emma",
            kid_age=6,
            story_type="custom",
            transcript="Short ID story",
            duration_seconds=100,
            audio_bytes=b"short audio",
            genre="bedtime",
        )
        
        retrieved = get_story_by_short_id(test_db, saved_story.short_id)
        assert retrieved is not None
        assert retrieved.id == "shortid-test-999"
        assert retrieved.short_id == saved_story.short_id
    finally:
        config_module.settings.storage_path = original_storage


def test_get_story_by_short_id_not_found_returns_none(test_db):
    """Returns None for non-existent short ID"""
    result = get_story_by_short_id(test_db, "xxxxxxxx")
    assert result is None


def test_short_id_collision_generates_new_id(test_db, tmp_path, monkeypatch):
    """If short ID collides, generate a new one"""
    import app.config as config_module
    original_storage = config_module.settings.storage_path
    config_module.settings.storage_path = tmp_path
    
    try:
        # Mock generate_short_id to return collision first, then unique
        call_count = 0
        def mock_generate():
            nonlocal call_count
            call_count += 1
            return "collided" if call_count == 1 else "unique123"
        
        import app.db.crud as crud_module
        monkeypatch.setattr(crud_module, "generate_short_id", mock_generate)
        
        # Save first story with "collided" ID
        story1 = save_story(
            db=test_db,
            story_id="story-1",
            title="First",
            kid_name="A",
            kid_age=5,
            story_type="custom",
            transcript="...",
            duration_seconds=100,
            audio_bytes=b"audio1",
        )
        assert story1.short_id == "collided"
        
        # Reset mock
        call_count = 0
        
        # Save second story - should detect collision and use "unique123"
        story2 = save_story(
            db=test_db,
            story_id="story-2",
            title="Second",
            kid_name="B",
            kid_age=6,
            story_type="custom",
            transcript="...",
            duration_seconds=120,
            audio_bytes=b"audio2",
        )
        assert story2.short_id == "unique123"
        assert call_count == 2  # Called twice due to collision
    finally:
        config_module.settings.storage_path = original_storage
