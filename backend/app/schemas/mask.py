"""Selection mask request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class PointIn(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class KeyframeIn(BaseModel):
    time: float = Field(ge=0)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class RectItem(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    type: Literal["rect"]
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)
    start_time: float = Field(ge=0)
    end_time: float = Field(ge=0)
    # Phase 6 optional fields (backward compatible)
    enabled: bool = True
    label: str | None = Field(default=None, max_length=120)
    keyframes: list[KeyframeIn] = Field(default_factory=list, max_length=5000)

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
    enabled: bool = True
    label: str | None = Field(default=None, max_length=120)

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, value: float, info: ValidationInfo) -> float:
        start = info.data.get("start_time")
        if start is not None and value < start:
            raise ValueError("end_time must be >= start_time")
        return value


class MaskGroup(BaseModel):
    """Named editable mask layer (Phase 6 multi-mask)."""

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    enabled: bool = True
    items: list[RectItem | BrushItem] = Field(default_factory=list, max_length=500)


class SelectionPayload(BaseModel):
    """
    Selection document.

    version=1 remains the default and is fully supported.
    version=2 may include `masks` groups; `items` is still accepted.
    """

    version: Literal[1, 2] = 1
    video_width: int = Field(gt=0)
    video_height: int = Field(gt=0)
    fps: float | None = Field(default=None, gt=0)
    items: list[RectItem | BrushItem] = Field(default_factory=list, max_length=500)
    masks: list[MaskGroup] = Field(default_factory=list, max_length=64)
    feather: int = Field(default=0, ge=0, le=64)
    expansion: int = Field(default=0, ge=0, le=64)
    edge_refine: int = Field(default=0, ge=0, le=16)


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
