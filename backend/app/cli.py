"""CLI management commands for Taleweaver.

Usage:
    python -m app.cli create-invite           # Generate a new invite code
    python -m app.cli create-invite --base-url https://example.com
"""
import argparse
import sys

from app.db.database import SessionLocal, init_db
from app.db.migrate import run_migrations


def create_invite(base_url: str = "http://localhost"):
    """Generate a new invite code and print the signup URL."""
    from app.db.auth_crud import create_invite as _create_invite

    # Ensure DB is ready
    from app.db import models  # noqa: F401
    init_db()
    run_migrations()

    db = SessionLocal()
    try:
        invite = _create_invite(db)
        url = f"{base_url.rstrip('/')}/signup?invite={invite.code}"
        print(f"Invite code: {invite.code}")
        print(f"Signup URL:  {url}")
        return invite.code
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Taleweaver CLI")
    subparsers = parser.add_subparsers(dest="command")

    invite_parser = subparsers.add_parser("create-invite", help="Generate a new invite code")
    invite_parser.add_argument(
        "--base-url",
        default="http://localhost",
        help="Base URL for the signup link (default: http://localhost)",
    )

    args = parser.parse_args()

    if args.command == "create-invite":
        create_invite(args.base_url)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
