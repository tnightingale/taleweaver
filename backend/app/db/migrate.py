"""
Database migration utility
Automatically runs schema updates on startup
"""
import logging
import sqlite3
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


def run_migrations():
    """
    Run all pending database migrations.
    
    This is called on application startup to ensure database schema is up-to-date.
    Uses SQLite ALTER TABLE which is safe for existing data.
    """
    db_path = settings.storage_path / "taleweaver.db"
    
    if not db_path.exists():
        logger.info("Database doesn't exist yet - will be created by init_db()")
        return
    
    logger.info("Checking for pending database migrations...")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        migrations_applied = []
        
        # Check if stories table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stories'")
        stories_exists = cursor.fetchone() is not None
        
        # Get existing columns in stories table (if it exists)
        existing_columns = set()
        if stories_exists:
            cursor.execute("PRAGMA table_info(stories)")
            existing_columns = {row[1] for row in cursor.fetchall()}
        
        # Migration 1: Add illustration fields to stories (2026-03-22)
        if stories_exists and "art_style" not in existing_columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN art_style TEXT")
            migrations_applied.append("stories.art_style")
            logger.info("✅ Added column: stories.art_style")
        
        if stories_exists and "has_illustrations" not in existing_columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN has_illustrations INTEGER DEFAULT 0 NOT NULL")
            migrations_applied.append("stories.has_illustrations")
            logger.info("✅ Added column: stories.has_illustrations")
        
        if stories_exists and "scene_data" not in existing_columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN scene_data TEXT")
            migrations_applied.append("stories.scene_data")
            logger.info("✅ Added column: stories.scene_data")
        
        # Migration 2: Create job_state table (2026-03-22)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_state'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE job_state (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'processing',
                    current_stage TEXT,
                    stages TEXT,
                    progress REAL DEFAULT 0.0,
                    progress_detail TEXT,
                    title TEXT,
                    duration_seconds INTEGER,
                    transcript TEXT,
                    short_id TEXT,
                    art_style TEXT,
                    scenes_json TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX idx_job_status ON job_state(status)')
            cursor.execute('CREATE INDEX idx_job_created ON job_state(created_at)')
            migrations_applied.append("job_state table")
            logger.info("✅ Created table: job_state with indexes")
        
        # Migration 3: Add resume fields to job_state (2026-03-22)
        cursor.execute("PRAGMA table_info(job_state)")
        job_state_columns = {row[1] for row in cursor.fetchall()}
        
        if "resumable" not in job_state_columns:
            cursor.execute("ALTER TABLE job_state ADD COLUMN resumable INTEGER DEFAULT 0 NOT NULL")
            migrations_applied.append("job_state.resumable")
            logger.info("✅ Added column: job_state.resumable")
        
        if "partial_data_json" not in job_state_columns:
            cursor.execute("ALTER TABLE job_state ADD COLUMN partial_data_json TEXT")
            migrations_applied.append("job_state.partial_data_json")
            logger.info("✅ Added column: job_state.partial_data_json")
        
        if "checkpoint_node" not in job_state_columns:
            cursor.execute("ALTER TABLE job_state ADD COLUMN checkpoint_node TEXT")
            migrations_applied.append("job_state.checkpoint_node")
            logger.info("✅ Added column: job_state.checkpoint_node")
        
        if "retry_count" not in job_state_columns:
            cursor.execute("ALTER TABLE job_state ADD COLUMN retry_count INTEGER DEFAULT 0 NOT NULL")
            migrations_applied.append("job_state.retry_count")
            logger.info("✅ Added column: job_state.retry_count")
        
        conn.commit()
        
        if migrations_applied:
            logger.info(f"✅ Database migrations complete: {', '.join(migrations_applied)}")
        else:
            logger.info("✅ Database schema is up-to-date")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
