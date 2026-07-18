"""Processing job request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.mask import SelectionPayload


class JobCreateRequest(BaseModel):
    strategy: Literal["blur", "fill", "classic_inpaint", "ai_inpaint"] = (
        "classic_inpaint"
    )
    mask_id: str | None = None
    payload: SelectionPayload | None = None
    prefer_gpu: bool = True
    export_format: Literal["mp4", "mov"] = "mp4"
    blur_ksize: int = Field(default=31, ge=3, le=151)
    fill_color_bgr: tuple[int, int, int] = (0, 0, 0)
    inpaint_radius: int = Field(default=3, ge=1, le=20)
    inpaint_method: Literal["telea", "ns"] = "telea"
    # LaMa options (used when strategy=ai_inpaint)
    padding: int = Field(default=64, ge=0, le=256)
    blend_strength: float = Field(default=1.0, ge=0.0, le=1.0)
    feather_radius: int = Field(default=12, ge=0, le=64)


class JobProgressOut(BaseModel):
    id: str
    status: str
    frames_total: int
    frames_done: int
    percent: float
    message: str | None = None
    device_used: str | None = None
    error: str | None = None
    fps: float | None = None
    eta_seconds: float | None = None
    model_loaded: bool | None = None


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
    export_format: str = "mp4"
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
    lama: dict | None = None


class AppSettingsOut(BaseModel):
    lama_model_dir: str
    lama_prefer_gpu: bool
    lama_cpu_threads: int
    lama_padding: int
    lama_blend_strength: float
    lama_feather_radius: int
    processing_temp_dir: str
    storage_root: str


class AppSettingsUpdate(BaseModel):
    lama_model_dir: str | None = None
    lama_prefer_gpu: bool | None = None
    lama_cpu_threads: int | None = Field(default=None, ge=0, le=128)
    lama_padding: int | None = Field(default=None, ge=0, le=256)
    lama_blend_strength: float | None = Field(default=None, ge=0.0, le=1.0)
    lama_feather_radius: int | None = Field(default=None, ge=0, le=64)
    processing_temp_dir: str | None = None
