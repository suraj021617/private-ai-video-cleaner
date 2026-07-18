"""System health tests."""

from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_health(app_client: AsyncClient) -> None:
    response = await app_client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["phase"] == "3-video-editor"


@pytest.mark.asyncio
async def test_ready(app_client: AsyncClient) -> None:
    response = await app_client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["storage_writable"] is True
    assert body["ffmpeg_available"] is True
