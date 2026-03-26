"""Tests for account update endpoint (PATCH /api/auth/me)"""


def test_change_password_success(test_client):
    """Changing password with correct current password succeeds."""
    response = test_client.patch(
        "/api/auth/me",
        json={"current_password": "testpassword", "new_password": "newpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

    # Verify new password works for login
    login_resp = test_client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "newpassword123"},
    )
    assert login_resp.status_code == 200


def test_change_password_wrong_current(test_client):
    """Changing password with wrong current password fails."""
    response = test_client.patch(
        "/api/auth/me",
        json={"current_password": "wrongpassword", "new_password": "newpassword123"},
    )
    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


def test_change_password_too_short(test_client):
    """New password under 8 characters is rejected."""
    response = test_client.patch(
        "/api/auth/me",
        json={"current_password": "testpassword", "new_password": "short"},
    )
    assert response.status_code == 400
    assert "8 characters" in response.json()["detail"]


def test_change_password_missing_current(test_client):
    """Changing password without current_password is rejected."""
    response = test_client.patch(
        "/api/auth/me",
        json={"new_password": "newpassword123"},
    )
    assert response.status_code == 400
    assert "current password" in response.json()["detail"].lower()


def test_update_display_name(test_client):
    """Updating display name succeeds and returns new name."""
    response = test_client.patch(
        "/api/auth/me",
        json={"display_name": "New Name"},
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "New Name"

    # Verify /me reflects the change
    me_resp = test_client.get("/api/auth/me")
    assert me_resp.json()["display_name"] == "New Name"


def test_update_display_name_empty(test_client):
    """Empty display name is rejected."""
    response = test_client.patch(
        "/api/auth/me",
        json={"display_name": "   "},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_update_account_unauthenticated(test_db):
    """Unauthenticated requests get 401."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.patch(
        "/api/auth/me",
        json={"display_name": "Hacker"},
    )
    assert response.status_code == 401
