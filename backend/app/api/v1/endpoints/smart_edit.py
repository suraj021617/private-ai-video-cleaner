"""Smart AI editing endpoints: detect, track, refine, thumbnails."""

from __future__ import annotations

import base64
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, require_auth
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.processing.mask_raster import rasterize_mask
from app.schemas.smart_edit import (
    DetectRequest,
    DetectResponse,
    DetectedObjectOut,
    RefineMaskRequest,
    RefineMaskResponse,
    ThumbnailsRequest,
    ThumbnailsResponse,
    TrackRequest,
    TrackResponse,
)
from app.services.smart_edit import (
    detect_objects_in_frame,
    detection_to_rect_item,
    extract_timeline_thumbnails,
    track_box_across_frames,
)
from app.services.video import VideoService

router = APIRouter(tags=["smart-edit"])


def get_video_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VideoService:
    return VideoService(db, settings)


def _read_frame_at(path: Path, time_seconds: float) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise AppError(code="video_open_failed", message="Cannot open video", status_code=422)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    frame_idx = max(0, int(time_seconds * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise AppError(code="frame_read_failed", message="Cannot read frame", status_code=422)
    return frame


@router.post("/videos/{video_id}/smart/detect", response_model=DetectResponse)
async def detect_objects(
    video_id: str,
    body: DetectRequest,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
) -> DetectResponse:
    video = await videos.get_owned(video_id, auth.user.id)
    frame = _read_frame_at(Path(video.storage_path), body.time_seconds)
    detected = detect_objects_in_frame(frame, max_objects=body.max_objects)
    duration = float(video.duration_seconds or 5.0)
    end = min(duration, body.time_seconds + 2.0)
    items = [
        detection_to_rect_item(det, start=body.time_seconds, end=max(end, body.time_seconds + 0.1))
        for det in detected
    ]
    return DetectResponse(
        objects=[DetectedObjectOut(**det.__dict__) for det in detected],
        items=items,
    )


@router.post("/videos/{video_id}/smart/track", response_model=TrackResponse)
async def track_object(
    video_id: str,
    body: TrackRequest,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
) -> TrackResponse:
    video = await videos.get_owned(video_id, auth.user.id)
    keyframes = track_box_across_frames(
        Path(video.storage_path),
        start_time=body.start_time,
        box_norm={"x": body.x, "y": body.y, "w": body.w, "h": body.h},
        max_seconds=body.max_seconds,
    )
    return TrackResponse(keyframes=keyframes)


@router.post("/videos/{video_id}/smart/refine", response_model=RefineMaskResponse)
async def refine_mask(
    video_id: str,
    body: RefineMaskRequest,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
) -> RefineMaskResponse:
    await videos.get_owned(video_id, auth.user.id)
    payload = dict(body.payload)
    payload["expansion"] = body.expansion
    payload["feather"] = body.feather
    payload["edge_refine"] = body.edge_refine
    mask = rasterize_mask(
        payload=payload,
        frame_width=body.width,
        frame_height=body.height,
        time_seconds=body.time_seconds,
    )
    ok, buf = cv2.imencode(".png", mask)
    if not ok:
        raise AppError(code="mask_encode_failed", message="Failed to encode mask", status_code=500)
    return RefineMaskResponse(
        mask_png_base64=base64.b64encode(buf.tobytes()).decode("ascii"),
        width=body.width,
        height=body.height,
    )


@router.post("/videos/{video_id}/smart/thumbnails", response_model=ThumbnailsResponse)
async def timeline_thumbnails(
    video_id: str,
    body: ThumbnailsRequest,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
) -> ThumbnailsResponse:
    video = await videos.get_owned(video_id, auth.user.id)
    thumbs = extract_timeline_thumbnails(
        Path(video.storage_path),
        count=body.count,
        max_width=body.max_width,
    )
    return ThumbnailsResponse(thumbnails=thumbs)
