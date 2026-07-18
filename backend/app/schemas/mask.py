"""Selection mask request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class PointIn(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class RectItem(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    type: Literal["rect"]
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, value: float, info: ValidationInfo) -> float:
        start = info.data.get("start_time")
        if start is not None and value < start:
            raise ValueError("end_time must be >= start_time")
        return value


class BrushItem(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    type: Literal["brush"]
    points: list[PointIn] = Field(min_length=1, max_length=20000)
    size: float = Field(gt=0, le=0.5)
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, value: float, info: ValidationInfo) -> float:
        start = info.data.get("start_time")
        if start is not None and value < start:
            raise ValueError("end_time must be >= start_time")
        return value


class SelectionPayload(BaseModel):
    version: Literal[1] = 1
    video_width: int = Field(gt=0)
    video_height: int = Field(gt=0)
    fps: float | None = Field(default=None, gt=0)
    items: list[RectItem | BrushItem] = Field(default_factory=list, max_length=500)


class MaskCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    payload: SelectionPayload


class MaskUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    payload: SelectionPayload | None = None


class MaskSummaryOut(BaseModel):
    id: str
    video_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    item_count: int


class MaskOut(MaskSummaryOut):
    payload: dict[str, Any]


class MaskListResponse(BaseModel):
    items: list[MaskSummaryOut]
    total: int
