"""Rasterize editor selection payloads into per-frame binary masks."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from app.core.errors import AppError
from app.services.smart_edit import (
    expand_mask_pixels,
    feather_mask_pixels,
    refine_mask_edges,
)


def _active(item: dict[str, Any], time_seconds: float) -> bool:
    if item.get("enabled") is False:
        return False
    start = float(item.get("start_time", 0.0))
    end = float(item.get("end_time", 0.0))
    return time_seconds >= start - 1e-4 and time_seconds <= end + 1e-4


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _interpolate_keyframes(
    keyframes: list[dict[str, Any]], time_seconds: float
) -> dict[str, float] | None:
    """Interpolate normalized rect from keyframes at/around time_seconds."""
    if not keyframes:
        return None
    ordered = sorted(keyframes, key=lambda k: float(k.get("time", 0.0)))
    if time_seconds <= float(ordered[0].get("time", 0.0)):
        k = ordered[0]
        return {
            "x": float(k["x"]),
            "y": float(k["y"]),
            "w": float(k["w"]),
            "h": float(k["h"]),
        }
    if time_seconds >= float(ordered[-1].get("time", 0.0)):
        k = ordered[-1]
        return {
            "x": float(k["x"]),
            "y": float(k["y"]),
            "w": float(k["w"]),
            "h": float(k["h"]),
        }
    for i in range(1, len(ordered)):
        left = ordered[i - 1]
        right = ordered[i]
        t0 = float(left.get("time", 0.0))
        t1 = float(right.get("time", 0.0))
        if time_seconds <= t1:
            span = max(t1 - t0, 1e-9)
            t = (time_seconds - t0) / span
            return {
                "x": _lerp(float(left["x"]), float(right["x"]), t),
                "y": _lerp(float(left["y"]), float(right["y"]), t),
                "w": _lerp(float(left["w"]), float(right["w"]), t),
                "h": _lerp(float(left["h"]), float(right["h"]), t),
            }
    return None


def _collect_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Collect drawable items from v1 `items` and optional v2 `masks[].items`.

    Backward compatible: payloads with only `items` continue to work.
    """
    items: list[dict[str, Any]] = list(payload.get("items") or [])
    for group in payload.get("masks") or []:
        if group.get("enabled") is False:
            continue
        for item in group.get("items") or []:
            items.append(item)
    return items


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

    Optional payload-level polish (applied after geometry):
    - expansion (pixels)
    - edge_refine (morph amount)
    - feather (blur radius; soft edges for preview/export blend)
    """
    if frame_width <= 0 or frame_height <= 0:
        raise AppError(
            code="invalid_frame_size",
            message="Frame dimensions must be positive",
            status_code=500,
        )

    mask = np.zeros((frame_height, frame_width), dtype=np.uint8)
    items = _collect_items(payload)
    if not items:
        return mask

    for item in items:
        if not _active(item, time_seconds):
            continue
        kind = item.get("type")
        if kind == "rect":
            _draw_rect(mask, item, frame_width, frame_height, time_seconds)
        elif kind == "brush":
            _draw_brush(mask, item, frame_width, frame_height)

    expansion = int(payload.get("expansion", 0) or 0)
    edge_refine = int(payload.get("edge_refine", 0) or 0)
    feather = int(payload.get("feather", 0) or 0)

    if expansion > 0:
        mask = expand_mask_pixels(mask, expansion)
    if edge_refine > 0:
        mask = refine_mask_edges(mask, amount=edge_refine)
    if feather > 0:
        # Soft alpha for blend; pipeline plugins treat >0 as inside.
        soft = feather_mask_pixels(mask, feather)
        mask = soft

    return mask


def _draw_rect(
    mask: np.ndarray,
    item: dict[str, Any],
    width: int,
    height: int,
    time_seconds: float,
) -> None:
    keyframes = item.get("keyframes") or []
    if keyframes:
        box = _interpolate_keyframes(keyframes, time_seconds)
        if box is None:
            return
        x_n, y_n, w_n, h_n = box["x"], box["y"], box["w"], box["h"]
    else:
        x_n = float(item["x"])
        y_n = float(item["y"])
        w_n = float(item["w"])
        h_n = float(item["h"])

    x = int(round(x_n * width))
    y = int(round(y_n * height))
    w = int(round(w_n * width))
    h = int(round(h_n * height))
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
