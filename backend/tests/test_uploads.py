"""Upload, progress, metadata, and video API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.conftest import bootstrap_and_login


async def _upload_file(
    client: AsyncClient,
    path: Path,
    csrf: str,
    *,
    content_type: str = "video/mp4",
) -> dict:
    data = path.read_bytes()
    init = await client.post(
        "/api/v1/uploads",
        headers={"X-CSRF-Token": csrf},
        json={
            "filename": path.name,
            "size_bytes": len(data),
            "content_type": content_type,
        },
    )
    assert init.status_code == 200, init.text
    upload = init.json()
    chunk_size = upload["chunk_size"]
    upload_id = upload["id"]

    for index in range(upload["chunks_total"]):
        start = index * chunk_size
        chunk = data[start : start + chunk_size]
        put = await client.put(
            f"/api/v1/uploads/{upload_id}/chunks/{index}",
            headers={
                "X-CSRF-Token": csrf,
                "Content-Type": "application/octet-stream",
            },
            content=chunk,
        )
        assert put.status_code == 200, put.text
        progress = put.json()
        assert progress["chunks_received"] == index + 1

    progress = await client.get(f"/api/v1/uploads/{upload_id}/progress")
    assert progress.status_code == 200
    assert progress.json()["status"] == "uploading"
    assert progress.json()["percent"] == 100.0

    complete = await client.post(
        f"/api/v1/uploads/{upload_id}/complete",
        headers={"X-CSRF-Token": csrf},
    )
    assert complete.status_code == 200, complete.text
    return complete.json()


@pytest.mark.asyncio
async def test_upload_progress_metadata_and_stream(
    app_client: AsyncClient, sample_video: Path
) -> None:
    auth = await bootstrap_and_login(app_client)
    csrf = auth["csrf_token"]

    video = await _upload_file(app_client, sample_video, csrf)
    assert video["status"] == "ready"
    assert video["metadata"]["width"] == 320
    assert video["metadata"]["height"] == 240
    assert video["metadata"]["duration_seconds"] is not None
    assert video["metadata"]["video_codec"]

    listed = await app_client.get("/api/v1/videos")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == video["id"]

    meta = await app_client.get(f"/api/v1/videos/{video['id']}/metadata")
    assert meta.status_code == 200
    assert meta.json()["width"] == 320

    content = await app_client.get(f"/api/v1/videos/{video['id']}/content")
    assert content.status_code == 200
    assert len(content.content) == video["size_bytes"]

    ranged = await app_client.get(
        f"/api/v1/videos/{video['id']}/content",
        headers={"Range": "bytes=0-9"},
    )
    assert ranged.status_code == 206
    assert ranged.headers["content-range"].startswith("bytes 0-9/")
    assert len(ranged.content) == 10

    deleted = await app_client.delete(
        f"/api/v1/videos/{video['id']}",
        headers={"X-CSRF-Token": csrf},
    )
    assert deleted.status_code == 204

    missing = await app_client.get(f"/api/v1/videos/{video['id']}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_rejects_bad_extension_and_oversize(
    app_client: AsyncClient, sample_video: Path, temp_env
) -> None:
    auth = await bootstrap_and_login(app_client)
    csrf = auth["csrf_token"]

    bad_ext = await app_client.post(
        "/api/v1/uploads",
        headers={"X-CSRF-Token": csrf},
        json={
            "filename": "notes.exe",
            "size_bytes": 100,
            "content_type": "video/mp4",
        },
    )
    assert bad_ext.status_code == 415

    too_big = await app_client.post(
        "/api/v1/uploads",
        headers={"X-CSRF-Token": csrf},
        json={
            "filename": "huge.mp4",
            "size_bytes": temp_env.max_upload_bytes + 1,
            "content_type": "video/mp4",
        },
    )
    assert too_big.status_code == 413

    # Unauthenticated blocked
    app_client.cookies.clear()
    unauth = await app_client.get("/api/v1/videos")
    assert unauth.status_code == 401


@pytest.mark.asyncio
async def test_cancel_upload(app_client: AsyncClient, sample_video: Path) -> None:
    auth = await bootstrap_and_login(app_client)
    csrf = auth["csrf_token"]
    data = sample_video.read_bytes()

    init = await app_client.post(
        "/api/v1/uploads",
        headers={"X-CSRF-Token": csrf},
        json={
            "filename": "sample.mp4",
            "size_bytes": len(data),
            "content_type": "video/mp4",
        },
    )
    upload_id = init.json()["id"]

    await app_client.put(
        f"/api/v1/uploads/{upload_id}/chunks/0",
        headers={"X-CSRF-Token": csrf, "Content-Type": "application/octet-stream"},
        content=data[: init.json()["chunk_size"]],
    )

    cancel = await app_client.delete(
        f"/api/v1/uploads/{upload_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert cancel.status_code == 204

    progress = await app_client.get(f"/api/v1/uploads/{upload_id}/progress")
    assert progress.status_code == 200
    assert progress.json()["status"] == "cancelled"
