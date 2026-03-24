"""FastAPI dependencies for authentication"""
from typing import Optional

from fastapi import HTTPException, Request

import app.db.database as _db_module
from app.db.models import Story, User

from .tokens import verify_token


def get_current_user(request: Request) -> User:
    """FastAPI dependency: require authenticated user from access_token cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(token, expected_type="access")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    db = _db_module.SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # Detach from session so it can be used after db.close()
        db.expunge(user)
        return user
    finally:
        db.close()


def get_optional_user(request: Request) -> Optional[User]:
    """FastAPI dependency: return user if authenticated, None otherwise."""
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = verify_token(token, expected_type="access")
    if not payload:
        return None

    user_id = payload.get("sub")
    db = _db_module.SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.expunge(user)
        return user
    finally:
        db.close()


def verify_story_ownership(story: Story, user: User):
    """Raise 403 if user doesn't own the story."""
    if story.user_id and story.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your story")
