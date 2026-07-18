"""Phase 6 smart editing tests."""

from __future__ import annotations

import numpy as np
import pytest
from httpx import AsyncClient

from app.processing.mask_raster import rasterize_mask
from app.processing.strategies import list_strategies, resolve_strategy
from app.processing.types import ProcessingStrategy
from app.services.smart_edit import (
    detect_objects_in_frame,
    expand_mask_pixels,
    feather_mask_pixels,
    refine_mask_edges,
)
from tests.conftest import bootstrap_and_login
from tests.test_uploads import _upload_file


def test_detect_objects_returns_boxes() -> None:
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frame[30:80, 40:100] = (220, 40, 40)
    objects = detect_objects_in_frame(frame, max_objects=5)
    assert isinstance(objects, list)


def test_mask_expand_feather_refine() -> None:
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[20:40, 20:40] = 255
    expanded = expand_mask_pixels(mask, 2)
    assert int(expanded.sum()) > int(mask.sum())
    soft = feather_mask_pixels(mask, 3)
    assert soft.dtype == np.uint8
    refined = refine_mask_edges(mask, amount=1)
    assert refined.shape == mask.shape


def test_keyframe_interpolation_rasterize() -> None:
    payload = {
        "version": 2,
        "items": [
            {
                "id": "r1",
                "type": "rect",
                "x": 0.1,
                "y": 0.1,
                "w": 0.2,
                "h": 0.2,
                "start_time": 0,
                "end_time": 2,
                "keyframes": [
                    {"time": 0.0, "x": 0.0, "y": 0.0, "w": 0.2, "h": 0.2},
                    {"time": 2.0, "x": 0.5, "y": 0.0, "w": 0.2, "h": 0.2},
                ],
            }
        ],
        "expansion": 0,
        "feather": 0,
        "edge_refine": 0,
    }
    mask_start = rasterize_mask(
        payload=payload, frame_width=100, frame_height=100, time_seconds=0.0
    )
    mask_mid = rasterize_mask(
        payload=payload, frame_width=100, frame_height=100, time_seconds=1.0
    )
    assert mask_start[10, 10] == 255
    assert mask_mid[10, 10] == 0
    # At t=1.0, x interpolates to 0.25 → filled around column 30–45
    assert mask_mid[10, 35] == 255


def test_propainter_sttn_fallback_to_available() -> None:
    names = {item["name"] for item in list_strategies()}
    assert "propainter" in names
    assert "sttn" in names
    plugin, used, fallback_from = resolve_strategy(ProcessingStrategy.PROPAINTER)
    assert plugin is not None
    assert used in {
        ProcessingStrategy.PROPAINTER,
        ProcessingStrategy.AI_INPAINT,
        ProcessingStrategy.CLASSIC_INPAINT,
    }
    if used != ProcessingStrategy.PROPAINTER:
        assert fallback_from == ProcessingStrategy.PROPAINTER


@pytest.mark.asyncio
async def test_smart_detect_thumbnails_and_projects(
    app_client: AsyncClient, sample_video
) -> None:
    auth = await bootstrap_and_login(app_client)
    csrf = auth["csrf_token"]
    video = await _upload_file(app_client, sample_video, csrf)
    video_id = video["id"]
    headers = {"X-CSRF-Token": csrf}

    detect = await app_client.post(
        f"/api/v1/videos/{video_id}/smart/detect",
        headers=headers,
        json={"time_seconds": 0.0, "max_objects": 8},
    )
    assert detect.status_code == 200, detect.text
    body = detect.json()
    assert "objects" in body
    assert "items" in body

    thumbs = await app_client.post(
        f"/api/v1/videos/{video_id}/smart/thumbnails",
        headers=headers,
        json={"count": 4, "max_width": 80},
    )
    assert thumbs.status_code == 200, thumbs.text
    assert len(thumbs.json()["thumbnails"]) >= 1

    created = await app_client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "name": "Test project",
            "video_id": video_id,
            "payload": {
                "version": 1,
                "video_id": video_id,
                "selection": {"version": 1, "items": []},
                "timeline": {"zoom": 1, "current_time": 0},
                "settings": {"strategy": "ai_inpaint"},
                "undo_stack": [],
                "redo_stack": [],
            },
        },
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["id"]

    listed = await app_client.get("/api/v1/projects")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    got = await app_client.get(f"/api/v1/projects/{project_id}")
    assert got.status_code == 200
    assert got.json()["name"] == "Test project"
