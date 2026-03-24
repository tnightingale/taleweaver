from pathlib import Path

import yaml
from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api")

DATA_DIR = Path(__file__).parent.parent / "data"

# Load YAML data once at import time
with open(DATA_DIR / "genres.yaml") as f:
    _genres = yaml.safe_load(f)

with open(DATA_DIR / "historical_events.yaml") as f:
    _historical_events = yaml.safe_load(f)

with open(DATA_DIR / "art_styles.yaml") as f:
    _art_styles = yaml.safe_load(f)


@router.get("/genres")
async def get_genres(_user: User = Depends(get_current_user)):
    return _genres


@router.get("/historical-events")
async def get_historical_events(_user: User = Depends(get_current_user)):
    return _historical_events


@router.get("/art-styles")
async def get_art_styles(_user: User = Depends(get_current_user)):
    """Get available art style presets for story illustrations"""
    return _art_styles
