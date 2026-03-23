"""
Huey background job queue configuration.

Uses SqliteHuey so there's no external infrastructure dependency —
the queue is stored in a SQLite file on the same volume as taleweaver.db.
"""
from huey import SqliteHuey
from app.config import settings

huey = SqliteHuey(
    "taleweaver",
    filename=str(settings.storage_path / "huey.db"),
)
