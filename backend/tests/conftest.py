"""Shared pytest fixtures for Phase 2 API tests."""

from __future__ import annotations

import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.db.session import dispose_engine, get_db, init_db
from app.main import create_app


@pytest_asyncio.fixture()
async def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    storage = tmp_path / "storage"
    db_path = tmp_path / "test.db"
    storage.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-with-at-least-32-chars")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("STORAGE_ROOT", str(storage))
    monkeypatch.setenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))
    monkeypatch.setenv("UPLOAD_CHUNK_SIZE", str(64 * 1024))
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("CORS_ORIGINS", "http://testserver")
    monkeypatch.setenv("AUTH_RATE_LIMIT_ATTEMPTS", "100")
    monkeypatch.setenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")

    get_settings.cache_clear()
    await dispose_engine()

    app = create_app()
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    await dispose_engine()
    get_settings.cache_clear()


@pytest.fixture()
def temp_env(app_client: AsyncClient) -> object:
    """Expose settings for assertions that need configured limits."""
    return get_settings()


@pytest.fixture()
def sample_video(tmp_path: Path) -> Path:
    path = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


async def bootstrap_and_login(
    client: AsyncClient,
    *,
    email: str = "owner@example.com",
    password: str = "secure-password-123",
    display_name: str = "Owner",
) -> dict:
    response = await client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()
