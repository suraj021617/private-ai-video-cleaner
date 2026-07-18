"""Processing job request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.mask import SelectionPayload

StrategyLiteral = Literal[
    "blur",
    "fill",
    "classic_inpaint",
    "ai_inpaint",
    "propainter",
    "sttn",
]
ExportFormatLiteral = Literal["mp4", "mov", "mkv"]
ExportCodecLiteral = Literal["h264", "hevc"]
ExportQualityLiteral = Literal["fast", "balanced", "best"]


class JobCreateRequest(BaseModel):
    strategy: StrategyLiteral = "classic_inpaint"
    mask_id: str | None = None
    payload: SelectionPayload | None = None
    prefer_gpu: bool = True
    export_format: ExportFormatLiteral = "mp4"
    export_codec: ExportCodecLiteral = "h264"
    export_quality: ExportQualityLiteral = "balanced"
    # Optional 4K upscale/export target (None = preserve source)
    export_width: int | None = Field(default=None, ge=16, le=7680)
    export_height: int | None = Field(default=None, ge=16, le=4320)
    blur_ksize: int = Field(default=31, ge=3, le=151)
    fill_color_bgr: tuple[int, int, int] = (0, 0, 0)
    inpaint_radius: int = Field(default=3, ge=1, le=20)
    inpaint_method: Literal["telea", "ns"] = "telea"
    # LaMa / mask polish options
    padding: int = Field(default=64, ge=0, le=256)
    blend_strength: float = Field(default=1.0, ge=0.0, le=1.0)
    feather_radius: int = Field(default=12, ge=0, le=64)
    mask_expansion: int = Field(default=0, ge=0, le=64)
    edge_refine: int = Field(default=0, ge=0, le=16)


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
    strategy_used: str | None = None
    fallback_from: str | None = None
    queue_position: int | None = None


class JobOut(BaseModel):
    id: str
    video_id: str
    mask_id: str | None
    strategy: str
    strategy_used: str | None = None
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
    export_codec: str = "h264"
    export_quality: str = "balanced"
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    queue_position: int | None = None


class StrategyInfo(BaseModel):
    name: str
    available: bool
    fallback: list[str] = Field(default_factory=list)


class DeviceInfoResponse(BaseModel):
    cuda_devices: int
    opencl_available: bool
    selected: str
    strategies: list[StrategyInfo]
    lama: dict | None = None
    gpu_benchmark: dict | None = None
    memory: dict | None = None


class AppSettingsOut(BaseModel):
    lama_model_dir: str
    lama_prefer_gpu: bool
    lama_cpu_threads: int
    lama_padding: int
    lama_blend_strength: float
    lama_feather_radius: int
    processing_temp_dir: str
    storage_root: str
    max_concurrent_jobs: int = 1


class AppSettingsUpdate(BaseModel):
    lama_model_dir: str | None = None
    lama_prefer_gpu: bool | None = None
    lama_cpu_threads: int | None = Field(default=None, ge=0, le=128)
    lama_padding: int | None = Field(default=None, ge=0, le=256)
    lama_blend_strength: float | None = Field(default=None, ge=0.0, le=1.0)
    lama_feather_radius: int | None = Field(default=None, ge=0, le=64)
    processing_temp_dir: str | None = None
    max_concurrent_jobs: int | None = Field(default=None, ge=1, le=8)
