"""Selection mask API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.conftest import bootstrap_and_login
from tests.test_uploads import _upload_file


@pytest.mark.asyncio
async def test_mask_save_load_update_delete(
    app_client: AsyncClient, sample_video: Path
) -> None:
    auth = await bootstrap_and_login(app_client)
    csrf = auth["csrf_token"]
    video = await _upload_file(app_client, sample_video, csrf)

    create = await app_client.post(
        f"/api/v1/videos/{video['id']}/masks",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "Intro watermark",
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
                        "h": 0.15,
                        "start_time": 0,
                        "end_time": 1,
                    },
                    {
                        "id": "b1",
                        "type": "brush",
                        "points": [{"x": 0.5, "y": 0.5}, {"x": 0.55, "y": 0.52}],
                        "size": 0.04,
                        "start_time": 0,
                        "end_time": 1,
                    },
                ],
            },
        },
    )
    assert create.status_code == 200, create.text
    mask = create.json()
    assert mask["name"] == "Intro watermark"
    assert mask["item_count"] == 2

    listed = await app_client.get(f"/api/v1/videos/{video['id']}/masks")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    loaded = await app_client.get(
        f"/api/v1/videos/{video['id']}/masks/{mask['id']}"
    )
    assert loaded.status_code == 200
    assert loaded.json()["payload"]["items"][0]["type"] == "rect"

    updated = await app_client.put(
        f"/api/v1/videos/{video['id']}/masks/{mask['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"name": "Updated mask"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated mask"

    deleted = await app_client.delete(
        f"/api/v1/videos/{video['id']}/masks/{mask['id']}",
        headers={"X-CSRF-Token": csrf},
    )
    assert deleted.status_code == 204

    missing = await app_client.get(
        f"/api/v1/videos/{video['id']}/masks/{mask['id']}"
    )
    assert missing.status_code == 404
