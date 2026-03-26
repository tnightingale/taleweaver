"""Authentication routes: signup, login, logout, refresh, Google OAuth"""
import json
import logging
import secrets
from typing import Optional

from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr

from app.auth.dependencies import get_current_user
from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import create_access_token, create_refresh_token, verify_token
from app.config import settings
from app.db.auth_crud import (
    create_user,
    get_invite_by_code,
    get_user_by_email,
    get_user_by_google_id,
    get_user_by_id,
    redeem_invite,
    update_user_display_name,
    update_user_password,
)
import app.db.database as _db_module
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth")

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


# ── Request schemas ──


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    invite_code: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateAccountRequest(BaseModel):
    display_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


# ── Cookie helpers ──


def _set_auth_cookies(response, user_id: str):
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    secure = not settings.disable_ssl

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/api/auth",
    )


def _clear_auth_cookies(response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")


def _user_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
    }


# ── Endpoints ──


@router.post("/signup")
async def signup(request: SignupRequest):
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    db = _db_module.SessionLocal()
    try:
        # Validate invite code
        invite = get_invite_by_code(db, request.invite_code)
        if not invite:
            raise HTTPException(status_code=400, detail="Invalid invite code")
        if invite.used_by:
            raise HTTPException(status_code=400, detail="Invite code already used")

        # Check if email already registered
        if get_user_by_email(db, request.email):
            raise HTTPException(status_code=409, detail="Email already registered")

        user = create_user(
            db,
            email=request.email,
            display_name=request.display_name,
            password_hash=hash_password(request.password),
        )
        redeem_invite(db, invite, user.id)

        response = JSONResponse(content=_user_response(user), status_code=201)
        _set_auth_cookies(response, user.id)
        return response
    finally:
        db.close()


@router.post("/login")
async def login(request: LoginRequest):
    db = _db_module.SessionLocal()
    try:
        user = get_user_by_email(db, request.email)
        if not user or not user.password_hash:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        response = JSONResponse(content=_user_response(user))
        _set_auth_cookies(response, user.id)
        return response
    finally:
        db.close()


@router.post("/logout")
async def logout():
    response = JSONResponse(content={"ok": True})
    _clear_auth_cookies(response)
    return response


@router.post("/refresh")
async def refresh(request: Request):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = verify_token(token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload["sub"]

    # Verify user still exists
    db = _db_module.SessionLocal()
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
    finally:
        db.close()

    response = JSONResponse(content={"ok": True})
    # Only refresh the access token; refresh token stays valid
    access_token = create_access_token(user_id)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.disable_ssl,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    return response


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _user_response(user)


@router.patch("/me")
async def update_account(request: UpdateAccountRequest, user: User = Depends(get_current_user)):
    if request.new_password is not None:
        if not request.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        if len(request.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    db = _db_module.SessionLocal()
    try:
        db_user = get_user_by_id(db, user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        if request.new_password is not None:
            if not db_user.password_hash or not verify_password(request.current_password, db_user.password_hash):
                raise HTTPException(status_code=400, detail="Current password is incorrect")
            update_user_password(db, user.id, hash_password(request.new_password))

        if request.display_name is not None:
            if not request.display_name.strip():
                raise HTTPException(status_code=400, detail="Display name cannot be empty")
            db_user = update_user_display_name(db, user.id, request.display_name)

        # Re-fetch to get latest state
        db_user = get_user_by_id(db, user.id)
        return _user_response(db_user)
    finally:
        db.close()


# ── Google OAuth ──


def _get_google_redirect_uri(request: Request) -> str:
    """Build callback URL from the incoming request's origin."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))
    return f"{scheme}://{host}/api/auth/google/callback"


@router.get("/google")
async def google_login(request: Request, invite: Optional[str] = None):
    """Redirect to Google OAuth consent screen."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    redirect_uri = _get_google_redirect_uri(request)

    # Generate CSRF nonce and store in state + httpOnly cookie for validation in callback
    nonce = secrets.token_urlsafe(32)
    state = json.dumps({"invite": invite or "", "nonce": nonce})

    client = AsyncOAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=redirect_uri,
        scope="openid email profile",
    )
    uri, _ = client.create_authorization_url(GOOGLE_AUTHORIZE_URL, state=state)
    response = RedirectResponse(url=uri)
    response.set_cookie(
        key="oauth_nonce",
        value=nonce,
        httponly=True,
        secure=not settings.disable_ssl,
        samesite="lax",
        max_age=600,  # 10 minutes
        path="/api/auth",
    )
    return response


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str = ""):
    """Handle Google OAuth callback."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    # Parse state and validate CSRF nonce against cookie
    try:
        state_data = json.loads(state)
    except (json.JSONDecodeError, TypeError):
        state_data = {}

    state_nonce = state_data.get("nonce", "")
    cookie_nonce = request.cookies.get("oauth_nonce", "")
    if not state_nonce or not cookie_nonce or state_nonce != cookie_nonce:
        raise HTTPException(status_code=400, detail="Invalid OAuth state (possible CSRF)")

    invite_code = state_data.get("invite", "")

    redirect_uri = _get_google_redirect_uri(request)

    # Exchange code for token
    client = AsyncOAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=redirect_uri,
    )
    try:
        token = await client.fetch_token(GOOGLE_TOKEN_URL, code=code)
    except Exception as e:
        logger.error(f"Google OAuth token exchange failed: {e}")
        raise HTTPException(status_code=400, detail="Failed to authenticate with Google")

    # Get user info
    try:
        resp = await client.get(GOOGLE_USERINFO_URL)
        userinfo = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch Google user info: {e}")
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")
    finally:
        await client.aclose()

    google_id = userinfo.get("sub")
    email = userinfo.get("email")
    name = userinfo.get("name", email.split("@")[0] if email else "User")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Google did not return required user info")

    db = _db_module.SessionLocal()
    try:
        # Check if user already exists (by google_id or email)
        user = get_user_by_google_id(db, google_id)
        if not user:
            user = get_user_by_email(db, email)
            if user:
                # Link Google account to existing user
                from app.db.auth_crud import link_google_account
                link_google_account(db, user.id, google_id)
            else:
                # New user — requires invite
                if not invite_code:
                    return _oauth_error_redirect("Invite code required for new accounts")

                invite = get_invite_by_code(db, invite_code)
                if not invite or invite.used_by:
                    return _oauth_error_redirect("Invalid or already used invite code")

                user = create_user(
                    db,
                    email=email,
                    display_name=name,
                    google_id=google_id,
                )
                redeem_invite(db, invite, user.id)

        # Set cookies and redirect to app
        response = RedirectResponse(url="/", status_code=302)
        _set_auth_cookies(response, user.id)
        response.delete_cookie("oauth_nonce", path="/api/auth")
        return response
    finally:
        db.close()


def _oauth_error_redirect(message: str):
    """Redirect to signup page with error message."""
    from urllib.parse import quote
    return RedirectResponse(url=f"/login?error={quote(message)}", status_code=302)
