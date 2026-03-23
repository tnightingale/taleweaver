"""
Tests that SQLite is configured with WAL mode and busy_timeout.

WAL mode is required for safe concurrent access from multiple processes
(gunicorn API + huey background worker). Without it, cross-process
reads and writes will deadlock with SQLITE_BUSY errors.
"""
import pytest
from sqlalchemy import text


def test_sqlite_wal_mode_enabled(test_db):
    """SQLite must use WAL journal mode for concurrent process access."""
    result = test_db.execute(text("PRAGMA journal_mode")).fetchone()
    assert result[0] == "wal", (
        f"SQLite journal_mode is '{result[0]}', must be 'wal'. "
        "WAL mode is required for gunicorn + huey worker to access the DB concurrently."
    )


def test_sqlite_busy_timeout_set(test_db):
    """SQLite must have a busy_timeout so writes wait instead of failing immediately."""
    result = test_db.execute(text("PRAGMA busy_timeout")).fetchone()
    timeout_ms = result[0]
    assert timeout_ms >= 5000, (
        f"SQLite busy_timeout is {timeout_ms}ms, must be >= 5000ms. "
        "Without busy_timeout, concurrent writes from gunicorn and huey will fail with SQLITE_BUSY."
    )
