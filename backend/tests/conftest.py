"""
Shared pytest fixtures for test isolation
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from app.db.database import init_db


@pytest.fixture(scope="function")
def test_db():
    """
    Create a fresh isolated test database for each test.
    
    This fixture ensures:
    1. Each test gets its own temporary database
    2. No state is shared between tests
    3. Database is cleaned up after test completes
    
    Usage:
        def test_something(test_db):
            # test_db is a SQLAlchemy session
            story = save_story(db=test_db, ...)
    """
    test_dir = Path(tempfile.mkdtemp())
    test_db_path = test_dir / "test.db"
    
    # Override database URL
    import app.db.database as db_module
    original_url = db_module.SQLALCHEMY_DATABASE_URL
    original_engine = db_module.engine
    original_session = db_module.SessionLocal
    
    db_module.SQLALCHEMY_DATABASE_URL = f"sqlite:///{test_db_path}"
    
    # Recreate engine and session with same pragmas as production
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    db_module.engine = create_engine(
        db_module.SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

    @event.listens_for(db_module.engine, "connect")
    def _set_test_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_module.engine)
    
    # Import models FIRST to register them with Base.metadata
    from app.db import models  # noqa: F401 - Ensures Story and JobState are registered
    
    # Initialize tables with the NEW test engine
    from app.db.database import Base
    Base.metadata.create_all(bind=db_module.engine)  # Use test engine explicitly
    
    # Run migrations (adds any missing columns, though create_all should have made them)
    from app.db.migrate import run_migrations
    run_migrations()
    
    # Create and yield session
    session = db_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()
        
        # Restore original database configuration
        db_module.SQLALCHEMY_DATABASE_URL = original_url
        db_module.engine = original_engine
        db_module.SessionLocal = original_session
        
        # Cleanup temp directory
        shutil.rmtree(test_dir)


@pytest.fixture(scope="function")
def test_client(test_db):
    """
    Create a TestClient with isolated database for API endpoint tests.
    
    This fixture ensures the FastAPI TestClient uses the same isolated
    database as the test_db fixture, preventing state sharing between tests.
    
    Note: This fixture depends on test_db to ensure they share the same database.
    
    Usage:
        def test_api_endpoint(test_db, test_client):
            # Both use the same isolated database
            save_story(db=test_db, ...)  # Create data in test DB
            response = test_client.get("/api/stories")  # Client sees same data
    """
    from fastapi.testclient import TestClient
    from app.main import app
    
    # test_db fixture has already set up the isolated database
    # The app will use the same database connection through SessionLocal
    
    client = TestClient(app)
    yield client
