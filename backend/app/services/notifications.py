"""Push notification sender for story completion/failure events."""
import json
import logging
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import PushSubscription

logger = logging.getLogger(__name__)


def get_push_subscriptions(db: Session, user_id: str) -> list[PushSubscription]:
    return db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()


def delete_subscription(db: Session, sub_id: str):
    db.query(PushSubscription).filter(PushSubscription.id == sub_id).delete()
    db.commit()


def notify_story_complete(db: Session, user_id: str, title: str, short_id: str):
    """Send push notification to all user's subscribed devices."""
    if not settings.vapid_private_key:
        return

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.debug("pywebpush not installed, skipping push notification")
        return

    subscriptions = get_push_subscriptions(db, user_id)
    if not subscriptions:
        return

    payload = json.dumps({
        "type": "story_complete",
        "title": title,
        "short_id": short_id,
        "url": f"/s/{short_id}",
    })

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh_key, "auth": sub.auth_key},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_contact_email},
            )
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                delete_subscription(db, sub.id)
                logger.info(f"Removed expired push subscription {sub.id}")
            else:
                logger.warning(f"Push notification failed for {sub.id}: {e}")
        except Exception as e:
            logger.warning(f"Push notification error for {sub.id}: {e}")


def notify_story_failed(db: Session, user_id: str, job_id: str, error: str):
    """Notify user of generation failure."""
    if not settings.vapid_private_key:
        return

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return

    subscriptions = get_push_subscriptions(db, user_id)
    if not subscriptions:
        return

    payload = json.dumps({
        "type": "story_failed",
        "job_id": job_id,
        "error": error,
        "url": "/library",
    })

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh_key, "auth": sub.auth_key},
                },
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_contact_email},
            )
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                delete_subscription(db, sub.id)
            else:
                logger.warning(f"Push notification failed for {sub.id}: {e}")
        except Exception as e:
            logger.warning(f"Push notification error for {sub.id}: {e}")
