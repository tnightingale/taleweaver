"""Push notification subscription management endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.models import User, PushSubscription
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/push")


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: dict  # {"p256dh": "...", "auth": "..."}


@router.get("/vapid-key")
async def get_vapid_key():
    """Return the public VAPID key for push subscription."""
    if not settings.vapid_public_key:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"public_key": settings.vapid_public_key}


@router.post("/subscribe")
async def subscribe(request: SubscribeRequest, user: User = Depends(get_current_user)):
    """Store or update a push subscription for the authenticated user."""
    if not settings.vapid_public_key:
        raise HTTPException(status_code=503, detail="Push notifications not configured")

    db = SessionLocal()
    try:
        # Upsert by endpoint
        existing = db.query(PushSubscription).filter(
            PushSubscription.endpoint == request.endpoint
        ).first()

        if existing:
            existing.user_id = user.id
            existing.p256dh_key = request.keys.get("p256dh", "")
            existing.auth_key = request.keys.get("auth", "")
        else:
            sub = PushSubscription(
                user_id=user.id,
                endpoint=request.endpoint,
                p256dh_key=request.keys.get("p256dh", ""),
                auth_key=request.keys.get("auth", ""),
            )
            db.add(sub)

        db.commit()
        return {"status": "subscribed"}
    finally:
        db.close()


@router.delete("/subscribe")
async def unsubscribe(request: SubscribeRequest, user: User = Depends(get_current_user)):
    """Remove a push subscription by endpoint."""
    db = SessionLocal()
    try:
        deleted = db.query(PushSubscription).filter(
            PushSubscription.endpoint == request.endpoint,
            PushSubscription.user_id == user.id,
        ).delete(synchronize_session=False)
        db.commit()
        return {"status": "unsubscribed", "deleted": deleted}
    finally:
        db.close()


@router.get("/status")
async def push_status(user: User = Depends(get_current_user)):
    """Check if the current user has any active push subscriptions."""
    db = SessionLocal()
    try:
        count = db.query(PushSubscription).filter(
            PushSubscription.user_id == user.id
        ).count()
        return {"subscribed": count > 0}
    finally:
        db.close()
