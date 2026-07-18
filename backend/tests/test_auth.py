"""Authentication and session tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import bootstrap_and_login


@pytest.mark.asyncio
async def test_bootstrap_login_me_logout(app_client: AsyncClient) -> None:
    status = await app_client.get("/api/v1/auth/status")
    assert status.status_code == 200
    assert status.json()["bootstrap_required"] is True
    assert status.json()["authenticated"] is False

    data = await bootstrap_and_login(app_client)
    assert data["user"]["email"] == "owner@example.com"
    assert data["csrf_token"]
    assert app_client.cookies.get("pavc_session")
    assert app_client.cookies.get("pavc_csrf")

    me = await app_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["display_name"] == "Owner"

    # Second bootstrap rejected
    again = await app_client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "other@example.com",
            "password": "another-password-123",
            "display_name": "Other",
        },
    )
    assert again.status_code == 409

    logout = await app_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": data["csrf_token"]},
    )
    assert logout.status_code == 204

    me_after = await app_client.get("/api/v1/auth/me")
    assert me_after.status_code == 401


@pytest.mark.asyncio
async def test_login_and_csrf_enforcement(app_client: AsyncClient) -> None:
    await bootstrap_and_login(app_client)
    # Clear cookies to force fresh login
    app_client.cookies.clear()

    bad = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password-xxx"},
    )
    assert bad.status_code == 401

    ok = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "secure-password-123"},
    )
    assert ok.status_code == 200
    csrf = ok.json()["csrf_token"]

    # Mutating call without CSRF fails
    denied = await app_client.post("/api/v1/uploads", json={
        "filename": "a.mp4",
        "size_bytes": 100,
        "content_type": "video/mp4",
    })
    assert denied.status_code == 403

    allowed = await app_client.post(
        "/api/v1/uploads",
        headers={"X-CSRF-Token": csrf},
        json={
            "filename": "a.mp4",
            "size_bytes": 100,
            "content_type": "video/mp4",
        },
    )
    assert allowed.status_code == 200


@pytest.mark.asyncio
async def test_change_password_revokes_session(app_client: AsyncClient) -> None:
    data = await bootstrap_and_login(app_client)
    csrf = data["csrf_token"]

    changed = await app_client.post(
        "/api/v1/auth/change-password",
        headers={"X-CSRF-Token": csrf},
        json={
            "current_password": "secure-password-123",
            "new_password": "brand-new-password-99",
        },
    )
    assert changed.status_code == 204

    me = await app_client.get("/api/v1/auth/me")
    assert me.status_code == 401

    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "brand-new-password-99"},
    )
    assert login.status_code == 200
