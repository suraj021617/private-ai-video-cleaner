"""Smart editing: detect, track, refine masks (OpenCV-based, offline-friendly)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.core.errors import AppError


@dataclass
class DetectedObject:
    id: str
    label: str
    score: float
    x: float
    y: float
    w: float
    h: float


def _normalize_box(
    x: int, y: int, w: int, h: int, width: int, height: int
) -> dict[str, float]:
    return {
        "x": max(0.0, x / width),
        "y": max(0.0, y / height),
        "w": min(1.0, w / width),
        "h": min(1.0, h / height),
    }


def detect_objects_in_frame(
    frame_bgr: np.ndarray,
    *,
    max_objects: int = 12,
) -> list[DetectedObject]:
    """
    Automatic object proposals using saliency + contour analysis.

    This runs fully offline without cloud APIs. Results are editable masks.
    """
    if frame_bgr is None or frame_bgr.size == 0:
        raise AppError(code="invalid_frame", message="Empty frame", status_code=422)

    height, width = frame_bgr.shape[:2]
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Spectral residual saliency approximation
    float_gray = np.float32(blur)
    magnitude = cv2.dft(float_gray, flags=cv2.DFT_COMPLEX_OUTPUT)
    real, imag = magnitude[:, :, 0], magnitude[:, :, 1]
    mag = cv2.magnitude(real, imag) + 1e-6
    log_mag = np.log(mag)
    avg = cv2.blur(log_mag, (3, 3))
    spectral = np.exp(log_mag - avg)
    real = real * spectral / mag
    imag = imag * spectral / mag
    complex_img = np.dstack([real, imag])
    saliency = cv2.idft(complex_img, flags=cv2.DFT_SCALE | cv2.DFT_REAL_OUTPUT)
    saliency = cv2.GaussianBlur(cv2.magnitude(saliency, np.zeros_like(saliency)), (9, 9), 0)
    saliency = cv2.normalize(saliency, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, thresh = cv2.threshold(saliency, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    area_min = (width * height) * 0.002
    candidates: list[tuple[float, DetectedObject]] = []
    for idx, contour in enumerate(contours):
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < area_min or w < 8 or h < 8:
            continue
        score = float(area) / float(width * height)
        box = _normalize_box(x, y, w, h, width, height)
        candidates.append(
            (
                score,
                DetectedObject(
                    id=f"det_{idx}",
                    label="object",
                    score=round(min(0.99, score * 4), 3),
                    **box,
                ),
            )
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in candidates[:max_objects]]


def detection_to_rect_item(det: DetectedObject, *, start: float, end: float) -> dict[str, Any]:
    return {
        "id": det.id,
        "type": "rect",
        "x": det.x,
        "y": det.y,
        "w": max(0.01, det.w),
        "h": max(0.01, det.h),
        "start_time": start,
        "end_time": end,
    }


def expand_mask_pixels(mask: np.ndarray, pixels: int) -> np.ndarray:
    if pixels <= 0:
        return mask
    k = pixels * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    return cv2.dilate(mask, kernel, iterations=1)


def feather_mask_pixels(mask: np.ndarray, radius: int) -> np.ndarray:
    binary = (mask > 0).astype(np.uint8) * 255
    if radius <= 0:
        return binary
    k = radius * 2 + 1
    return cv2.GaussianBlur(binary, (k, k), 0)


def refine_mask_edges(mask: np.ndarray, *, amount: int = 2) -> np.ndarray:
    """Morphological open/close to clean jagged mask edges."""
    binary = (mask > 0).astype(np.uint8) * 255
    k = max(1, amount) * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    return closed


def track_box_across_frames(
    video_path: Path,
    *,
    start_time: float,
    box_norm: dict[str, float],
    max_seconds: float = 8.0,
) -> list[dict[str, Any]]:
    """
    Track a normalized box from start_time forward using OpenCV CSRT/KCF.

    Returns keyframes [{time, x,y,w,h}, ...]
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise AppError(code="video_open_failed", message="Cannot open video", status_code=422)

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    start_frame = max(0, int(start_time * fps))
    end_frame = start_frame + int(max(0.1, max_seconds) * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    ok, frame = cap.read()
    if not ok or frame is None:
        cap.release()
        raise AppError(code="frame_read_failed", message="Cannot read start frame", status_code=422)

    x = int(box_norm["x"] * width)
    y = int(box_norm["y"] * height)
    w = max(4, int(box_norm["w"] * width))
    h = max(4, int(box_norm["h"] * height))
    init_box = (x, y, w, h)

    tracker = None
    for factory in (
        lambda: cv2.TrackerCSRT_create(),
        lambda: cv2.TrackerKCF_create(),
        lambda: cv2.legacy.TrackerCSRT_create() if hasattr(cv2, "legacy") else None,
    ):
        try:
            tracker = factory()
            if tracker is not None:
                tracker.init(frame, init_box)
                break
        except Exception:  # noqa: BLE001
            tracker = None
    if tracker is None:
        cap.release()
        raise AppError(
            code="tracker_unavailable",
            message="No OpenCV tracker available in this build",
            status_code=503,
        )

    keyframes: list[dict[str, Any]] = [
        {
            "time": start_frame / fps,
            "x": box_norm["x"],
            "y": box_norm["y"],
            "w": box_norm["w"],
            "h": box_norm["h"],
        }
    ]
    frame_idx = start_frame
    sample_every = max(1, int(fps // 5))  # ~5 keyframes/sec
    while frame_idx < end_frame:
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        frame_idx += 1
        ok, box = tracker.update(frame)
        if not ok:
            break
        bx, by, bw, bh = [float(v) for v in box]
        if frame_idx % sample_every == 0 or frame_idx == end_frame - 1:
            keyframes.append(
                {
                    "time": frame_idx / fps,
                    **_normalize_box(int(bx), int(by), int(bw), int(bh), width, height),
                }
            )
    cap.release()
    return keyframes


def extract_timeline_thumbnails(
    video_path: Path,
    *,
    count: int = 12,
    max_width: int = 160,
) -> list[dict[str, Any]]:
    """Return base64 JPEG thumbnails evenly spaced across the timeline."""
    import base64

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise AppError(code="video_open_failed", message="Cannot open video", status_code=422)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    if frame_count <= 0:
        # fallback read
        frames = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
        frame_count = len(frames)
        cap.release()
        if frame_count == 0:
            raise AppError(code="empty_video", message="No frames found", status_code=422)
        indices = [int(i * (frame_count - 1) / max(count - 1, 1)) for i in range(count)]
        thumbs = []
        for idx in indices:
            frame = frames[idx]
            thumbs.append(_encode_thumb(frame, idx / fps if fps else 0, max_width))
        return thumbs

    indices = [int(i * (frame_count - 1) / max(count - 1, 1)) for i in range(count)]
    thumbs: list[dict[str, Any]] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        thumbs.append(_encode_thumb(frame, idx / fps if fps else 0, max_width))
    cap.release()
    return thumbs


def _encode_thumb(frame: np.ndarray, time_seconds: float, max_width: int) -> dict[str, Any]:
    import base64

    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / w
        frame = cv2.resize(frame, (max_width, max(1, int(h * scale))))
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
    if not ok:
        raise AppError(code="thumb_encode_failed", message="Thumbnail encode failed", status_code=500)
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return {
        "time": round(float(time_seconds), 3),
        "data_url": f"data:image/jpeg;base64,{b64}",
    }
