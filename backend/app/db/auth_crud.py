"""CRUD operations for users and invites"""
import secrets
import string
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .models import Invite, User


def generate_invite_code(length: int = 12) -> str:
    """Generate a random invite code like tw_abc123xyz456."""
    alphabet = string.ascii_lowercase + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"tw_{random_part}"


def create_user(
    db: Session,
    email: str,
    display_name: str,
    password_hash: Optional[str] = None,
    google_id: Optional[str] = None,
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        password_hash=password_hash,
        display_name=display_name.strip(),
        google_id=google_id,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
    return db.query(User).filter(User.google_id == google_id).first()


def link_google_account(db: Session, user_id: str, google_id: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.google_id = google_id
        db.commit()


# ── Invite operations ──


def create_invite(db: Session, created_by: Optional[str] = None) -> Invite:
    code = generate_invite_code()
    while db.query(Invite).filter(Invite.code == code).first():
        code = generate_invite_code()

    invite = Invite(
        id=str(uuid.uuid4()),
        code=code,
        created_by=created_by,
        created_at=datetime.utcnow(),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def get_invite_by_code(db: Session, code: str) -> Optional[Invite]:
    return db.query(Invite).filter(Invite.code == code).first()


def redeem_invite(db: Session, invite: Invite, user_id: str) -> None:
    invite.used_by = user_id
    invite.used_at = datetime.utcnow()
    db.commit()
