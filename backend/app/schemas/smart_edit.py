"""Smart editing request/response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DetectRequest(BaseModel):
    time_seconds: float = Field(default=0.0, ge=0)
    max_objects: int = Field(default=12, ge=1, le=40)


class DetectedObjectOut(BaseModel):
    id: str
    label: str
    score: float
    x: float
    y: float
    w: float
    h: float


class DetectResponse(BaseModel):
    objects: list[DetectedObjectOut]
    items: list[dict[str, Any]]


class TrackRequest(BaseModel):
    start_time: float = Field(ge=0)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)
    max_seconds: float = Field(default=8.0, gt=0, le=120)


class TrackResponse(BaseModel):
    keyframes: list[dict[str, Any]]


class RefineMaskRequest(BaseModel):
    payload: dict[str, Any]
    time_seconds: float = Field(default=0.0, ge=0)
    expansion: int = Field(default=0, ge=0, le=64)
    feather: int = Field(default=0, ge=0, le=64)
    edge_refine: int = Field(default=2, ge=0, le=16)
    width: int = Field(default=320, ge=16, le=4096)
    height: int = Field(default=180, ge=16, le=4096)


class RefineMaskResponse(BaseModel):
    mask_png_base64: str
    width: int
    height: int


class ThumbnailsRequest(BaseModel):
    count: int = Field(default=12, ge=2, le=48)
    max_width: int = Field(default=160, ge=32, le=640)


class ThumbnailsResponse(BaseModel):
    thumbnails: list[dict[str, Any]]


class PreviewMode(BaseModel):
    mode: Literal["before", "after", "split"] = "split"
