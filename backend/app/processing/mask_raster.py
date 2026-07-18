"""Rasterize editor selection payloads into per-frame binary masks."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from app.core.errors import AppError


def _active(item: dict[str, Any], time_seconds: float) -> bool:
    start = float(item.get("start_time", 0.0))
    end = float(item.get("end_time", 0.0))
    return time_seconds >= start - 1e-4 and time_seconds <= end + 1e-4


def rasterize_mask(
    *,
    payload: dict[str, Any],
    frame_width: int,
    frame_height: int,
    time_seconds: float,
) -> np.ndarray:
    """
    Build a uint8 mask (0 outside, 255 inside) for the given timestamp.

    Coordinates in the payload are normalized 0–1 relative to the editor
    video dimensions and are scaled to the actual frame size.
    """
    if frame_width <= 0 or frame_height <= 0:
        raise AppError(
            code="invalid_frame_size",
            message="Frame dimensions must be positive",
            status_code=500,
        )

    mask = np.zeros((frame_height, frame_width), dtype=np.uint8)
    items = payload.get("items") or []
    if not items:
        return mask

    for item in items:
        if not _active(item, time_seconds):
            continue
        kind = item.get("type")
        if kind == "rect":
            _draw_rect(mask, item, frame_width, frame_height)
        elif kind == "brush":
            _draw_brush(mask, item, frame_width, frame_height)

    return mask


def _draw_rect(
    mask: np.ndarray, item: dict[str, Any], width: int, height: int
) -> None:
    x = int(round(float(item["x"]) * width))
    y = int(round(float(item["y"]) * height))
    w = int(round(float(item["w"]) * width))
    h = int(round(float(item["h"]) * height))
    x2 = min(width, max(0, x + max(w, 1)))
    y2 = min(height, max(0, y + max(h, 1)))
    x1 = min(max(0, x), width)
    y1 = min(max(0, y), height)
    if x2 > x1 and y2 > y1:
        mask[y1:y2, x1:x2] = 255


def _draw_brush(
    mask: np.ndarray, item: dict[str, Any], width: int, height: int
) -> None:
    points = item.get("points") or []
    if not points:
        return
    radius = max(
        1, int(round(float(item.get("size", 0.03)) * min(width, height)))
    )
    pts = [
        (int(round(float(p["x"]) * width)), int(round(float(p["y"]) * height)))
        for p in points
    ]
    if len(pts) == 1:
        cv2.circle(mask, pts[0], radius, 255, thickness=-1, lineType=cv2.LINE_AA)
        return
    for i in range(1, len(pts)):
        cv2.line(mask, pts[i - 1], pts[i], 255, thickness=radius * 2, lineType=cv2.LINE_AA)
    cv2.circle(mask, pts[0], radius, 255, thickness=-1, lineType=cv2.LINE_AA)
    cv2.circle(mask, pts[-1], radius, 255, thickness=-1, lineType=cv2.LINE_AA)


def assert_outside_unchanged(
    original: np.ndarray, processed: np.ndarray, mask: np.ndarray
) -> None:
    """Safety check used in tests: pixels where mask==0 must be identical."""
    outside = mask == 0
    if not np.array_equal(original[outside], processed[outside]):
        raise AssertionError("Pixels outside the mask were modified")
