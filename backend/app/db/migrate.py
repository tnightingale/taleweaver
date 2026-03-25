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

        # Migration 4: Add story_params_json to job_state (for huey retry re-enqueue)
        if "story_params_json" not in job_state_columns:
            cursor.execute("ALTER TABLE job_state ADD COLUMN story_params_json TEXT")
            migrations_applied.append("job_state.story_params_json")
            logger.info("✅ Added column: job_state.story_params_json")

        # Migration 5: Add cover_image_path to stories (2026-03-23)
        if stories_exists and "cover_image_path" not in existing_columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN cover_image_path TEXT")
            migrations_applied.append("stories.cover_image_path")
            logger.info("✅ Added column: stories.cover_image_path")

        # Migration 6: Create users table (2026-03-24)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT,
                    display_name TEXT NOT NULL,
                    google_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            ''')
            cursor.execute('CREATE UNIQUE INDEX idx_users_email ON users(email)')
            cursor.execute('CREATE UNIQUE INDEX idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL')
            migrations_applied.append("users table")
            logger.info("✅ Created table: users")

        # Migration 7: Create invites table (2026-03-24)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invites'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE invites (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL UNIQUE,
                    created_by TEXT REFERENCES users(id),
                    used_by TEXT REFERENCES users(id),
                    used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
            ''')
            cursor.execute('CREATE UNIQUE INDEX idx_invites_code ON invites(code)')
            migrations_applied.append("invites table")
            logger.info("✅ Created table: invites")

        # Migration 8: Add user_id to stories (2026-03-24)
        # Re-read columns since they may have changed above
        if stories_exists:
            cursor.execute("PRAGMA table_info(stories)")
            existing_columns = {row[1] for row in cursor.fetchall()}
        if stories_exists and "user_id" not in existing_columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN user_id TEXT REFERENCES users(id)")
            cursor.execute('CREATE INDEX idx_stories_user_id ON stories(user_id)')
            migrations_applied.append("stories.user_id")
            logger.info("✅ Added column: stories.user_id")

        # Migration 9: Add user_id to job_state (2026-03-24)
        cursor.execute("PRAGMA table_info(job_state)")
        job_state_columns = {row[1] for row in cursor.fetchall()}
        if "user_id" not in job_state_columns:
            cursor.execute("ALTER TABLE job_state ADD COLUMN user_id TEXT")
            migrations_applied.append("job_state.user_id")
            logger.info("✅ Added column: job_state.user_id")

        # Migration 10: Assign orphaned stories to first registered user (2026-03-24)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            cursor.execute("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
            first_user = cursor.fetchone()
            if first_user:
                cursor.execute(
                    "UPDATE stories SET user_id = ? WHERE user_id IS NULL",
                    (first_user[0],)
                )
                orphaned = cursor.rowcount
                if orphaned:
                    migrations_applied.append(f"assigned {orphaned} orphaned stories")
                    logger.info(f"✅ Assigned {orphaned} orphaned stories to first user")

        # Migration 11: Add video_path to stories (2026-03-24)
        # Re-read columns since they may have changed above
        if stories_exists:
            cursor.execute("PRAGMA table_info(stories)")
            existing_columns = {row[1] for row in cursor.fetchall()}
        if stories_exists and "video_path" not in existing_columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN video_path TEXT")
            migrations_applied.append("stories.video_path")
            logger.info("✅ Added column: stories.video_path")

        # Migration 12: Create push_subscriptions table (2026-03-25)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='push_subscriptions'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE push_subscriptions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id),
                    endpoint TEXT NOT NULL UNIQUE,
                    p256dh_key TEXT NOT NULL,
                    auth_key TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX idx_push_sub_user ON push_subscriptions(user_id)')
            migrations_applied.append("push_subscriptions table")
            logger.info("✅ Created table: push_subscriptions")

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
