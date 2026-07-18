"""Processing job request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.mask import SelectionPayload


class JobCreateRequest(BaseModel):
    strategy: Literal["blur", "fill", "classic_inpaint"] = "classic_inpaint"
    mask_id: str | None = None
    payload: SelectionPayload | None = None
    prefer_gpu: bool = True
    blur_ksize: int = Field(default=31, ge=3, le=151)
    fill_color_bgr: tuple[int, int, int] = (0, 0, 0)
    inpaint_radius: int = Field(default=3, ge=1, le=20)
    inpaint_method: Literal["telea", "ns"] = "telea"


class JobProgressOut(BaseModel):
    id: str
    status: str
    frames_total: int
    frames_done: int
    percent: float
    message: str | None = None
    device_used: str | None = None
    error: str | None = None


class JobOut(BaseModel):
    id: str
    video_id: str
    mask_id: str | None
    strategy: str
    status: str
    prefer_gpu: bool
    device_used: str | None
    frames_total: int
    frames_done: int
    percent: float
    message: str | None
    error_message: str | None
    download_ready: bool
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class StrategyInfo(BaseModel):
    name: str
    available: bool


class DeviceInfoResponse(BaseModel):
    cuda_devices: int
    opencl_available: bool
    selected: str
    strategies: list[StrategyInfo]
