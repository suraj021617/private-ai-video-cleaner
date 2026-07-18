"""Unit and integration tests for the processing engine."""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from httpx import AsyncClient

from app.processing.mask_raster import assert_outside_unchanged, rasterize_mask
from app.processing.pipeline import VideoProcessingPipeline
from app.processing.strategies.blur import BlurPlugin
from app.processing.strategies.fill import FillPlugin
from app.processing.types import (
    ComputeDevice,
    FrameContext,
    ProcessingStrategy,
    StrategyOptions,
)
from tests.conftest import bootstrap_and_login
from tests.test_uploads import _upload_file


def test_rasterize_rect_and_brush() -> None:
    payload = {
        "version": 1,
        "items": [
            {
                "id": "r1",
                "type": "rect",
                "x": 0.0,
                "y": 0.0,
                "w": 0.5,
                "h": 0.5,
                "start_time": 0,
                "end_time": 10,
            },
            {
                "id": "b1",
                "type": "brush",
                "points": [{"x": 0.8, "y": 0.8}],
                "size": 0.05,
                "start_time": 0,
                "end_time": 10,
            },
        ],
    }
    mask = rasterize_mask(
        payload=payload, frame_width=100, frame_height=100, time_seconds=1.0
    )
    assert mask[10, 10] == 255
    assert mask[90, 10] == 0
    assert mask[80, 80] == 255


def test_plugins_never_modify_outside_mask() -> None:
    frame = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[16:48, 16:48] = 255
    ctx = FrameContext(
        index=0,
        time_seconds=0.0,
        frame_bgr=frame.copy(),
        mask=mask,
        device=ComputeDevice.CPU,
    )
    for plugin in (BlurPlugin(), FillPlugin()):
        result = plugin.process_frame(ctx, StrategyOptions())
        assert_outside_unchanged(frame, result.frame_bgr, mask)
        assert result.pixels_modified == int(np.count_nonzero(mask))


def test_pipeline_preserves_fps_resolution_and_outside_pixels(
    tmp_path: Path, sample_video: Path
) -> None:
    payload = {
        "version": 1,
        "items": [
            {
                "id": "r1",
                "type": "rect",
                "x": 0.1,
                "y": 0.1,
                "w": 0.3,
                "h": 0.3,
                "start_time": 0,
                "end_time": 10,
            }
        ],
    }
    output = tmp_path / "out.mp4"
    work = tmp_path / "work"
    result = VideoProcessingPipeline(prefer_gpu=False).run(
        source_path=sample_video,
        output_path=output,
        work_dir=work,
        strategy=ProcessingStrategy.FILL,
        mask_payload=payload,
    )
    assert output.is_file()
    assert result["width"] == 320
    assert result["height"] == 240
    assert abs(result["fps"] - 25.0) < 0.5 or abs(result["fps"] - 30.0) < 5

    src = cv2.VideoCapture(str(sample_video))
    dst = cv2.VideoCapture(str(output))
    assert src.isOpened() and dst.isOpened()
    ok_s, frame_s = src.read()
    ok_d, frame_d = dst.read()
    src.release()
    dst.release()
    assert ok_s and ok_d
    mask = rasterize_mask(
        payload=payload,
        frame_width=frame_s.shape[1],
        frame_height=frame_s.shape[0],
        time_seconds=0.0,
    )
    assert_outside_unchanged(frame_s, frame_d, mask)


@pytest.mark.asyncio
async def test_job_api_process_and_download(
    app_client: AsyncClient, sample_video: Path
) -> None:
    auth = await bootstrap_and_login(app_client)
    csrf = auth["csrf_token"]
    video = await _upload_file(app_client, sample_video, csrf)

    caps = await app_client.get("/api/v1/processing/capabilities")
    assert caps.status_code == 200
    assert "selected" in caps.json()

    created = await app_client.post(
        f"/api/v1/videos/{video['id']}/jobs",
        headers={"X-CSRF-Token": csrf},
        json={
            "strategy": "blur",
            "prefer_gpu": True,
            "payload": {
                "version": 1,
                "video_width": 320,
                "video_height": 240,
                "fps": 30,
                "items": [
                    {
                        "id": "r1",
                        "type": "rect",
                        "x": 0.2,
                        "y": 0.2,
                        "w": 0.4,
                        "h": 0.4,
                        "start_time": 0,
                        "end_time": 5,
                    }
                ],
            },
        },
    )
    assert created.status_code == 200, created.text
    job_id = created.json()["id"]

    deadline = time.time() + 60
    status = "queued"
    while time.time() < deadline:
        progress = await app_client.get(f"/api/v1/jobs/{job_id}/progress")
        assert progress.status_code == 200
        status = progress.json()["status"]
        if status in {"completed", "failed"}:
            break
        await _sleep(0.25)

    detail = await app_client.get(f"/api/v1/jobs/{job_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "completed", body
    assert body["download_ready"] is True

    download = await app_client.get(f"/api/v1/jobs/{job_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("video/")
    assert len(download.content) > 1000


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
