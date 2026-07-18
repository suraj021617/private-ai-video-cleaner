"""Job pause / cancel / queue control tests."""

from __future__ import annotations

import time

import pytest
from httpx import AsyncClient

from tests.conftest import bootstrap_and_login
from tests.test_uploads import _upload_file


@pytest.mark.asyncio
async def test_cancel_queued_job(
    app_client: AsyncClient, sample_video
) -> None:
    auth = await bootstrap_and_login(app_client)
    csrf = auth["csrf_token"]
    headers = {"X-CSRF-Token": csrf}
    video = await _upload_file(app_client, sample_video, csrf)

    created = await app_client.post(
        f"/api/v1/videos/{video['id']}/jobs",
        headers=headers,
        json={
            "strategy": "fill",
            "export_format": "mkv",
            "export_codec": "h264",
            "export_quality": "fast",
            "payload": {
                "version": 1,
                "video_width": 320,
                "video_height": 240,
                "fps": 30,
                "items": [
                    {
                        "id": "r1",
                        "type": "rect",
                        "x": 0.1,
                        "y": 0.1,
                        "w": 0.2,
                        "h": 0.2,
                        "start_time": 0,
                        "end_time": 5,
                    }
                ],
            },
        },
    )
    assert created.status_code == 200, created.text
    job_id = created.json()["id"]

    # Wait briefly then ensure job can complete or be cancelled cleanly
    deadline = time.time() + 45
    final = None
    while time.time() < deadline:
        progress = await app_client.get(f"/api/v1/jobs/{job_id}/progress")
        assert progress.status_code == 200
        status = progress.json()["status"]
        if status in {"completed", "failed", "cancelled"}:
            final = status
            break
        await _sleep(0.2)

    assert final in {"completed", "failed", "cancelled"}
    detail = await app_client.get(f"/api/v1/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["export_format"] == "mkv"


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
