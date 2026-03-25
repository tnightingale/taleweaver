"""JWT token creation and verification"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt

from app.config import settings


def _get_secret() -> str:
    """Get JWT signing secret, falling back to secret_key_base."""
    secret = settings.jwt_secret or settings.secret_key_base
    if not secret:
        raise RuntimeError(
            "No JWT secret configured. Set JWT_SECRET or SECRET_KEY_BASE."
        )
    return secret


def create_access_token(user_id: str) -> str:
    expires = datetime.utcnow() + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": expires,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    expires = datetime.utcnow() + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expires,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def verify_token(token: str, expected_type: str = "access") -> Optional[dict]:
    """Verify and decode a JWT token.

    Returns the decoded payload or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=["HS256"])
        if payload.get("type") != expected_type:
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
