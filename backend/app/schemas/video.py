"""Video schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoMetadataOut(BaseModel):
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    container: str | None = None
    bitrate: int | None = None


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: VideoMetadataOut


class VideoListResponse(BaseModel):
    items: list[VideoOut]
    total: int
