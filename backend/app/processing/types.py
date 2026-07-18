"""Processing domain types shared across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class ComputeDevice(str, Enum):
    CUDA = "cuda"
    OPENCL = "opencl"
    CPU = "cpu"


class ProcessingStrategy(str, Enum):
    BLUR = "blur"
    FILL = "fill"
    CLASSIC_INPAINT = "classic_inpaint"
    AI_INPAINT = "ai_inpaint"
    PROPAINTER = "propainter"
    STTN = "sttn"


class ExportCodec(str, Enum):
    H264 = "h264"
    HEVC = "hevc"


class ExportQuality(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    BEST = "best"


@dataclass(frozen=True)
class VideoStreamInfo:
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float
    has_audio: bool
    video_codec: str | None = None
    audio_codec: str | None = None
    pixel_format: str | None = None
    color_space: str | None = None
    color_transfer: str | None = None
    color_primaries: str | None = None
    rotation: int | None = None
    bit_rate: int | None = None
    hdr: bool = False


@dataclass
class FrameContext:
    """One decoded frame plus the binary mask to process."""

    index: int
    time_seconds: float
    frame_bgr: np.ndarray
    mask: np.ndarray  # uint8, 0 outside / 255 inside
    device: ComputeDevice


@dataclass
class StrategyOptions:
    """Options for classic strategies. AI plugins may extend via extras."""

    blur_ksize: int = 31
    fill_color_bgr: tuple[int, int, int] = (0, 0, 0)
    inpaint_radius: int = 3
    inpaint_method: str = "telea"  # telea | ns
    extras: dict[str, Any] = field(default_factory=dict)

    def normalized_ksize(self) -> int:
        k = int(self.blur_ksize)
        if k < 3:
            k = 3
        if k % 2 == 0:
            k += 1
        return k


@dataclass
class ProcessFrameResult:
    frame_bgr: np.ndarray
    strategy: ProcessingStrategy
    device: ComputeDevice
    pixels_modified: int


@dataclass
class PipelineProgress:
    status: str
    frames_total: int
    frames_done: int
    percent: float
    message: str | None = None
    device: str | None = None
    fps: float | None = None
    eta_seconds: float | None = None
    model_loaded: bool | None = None
    strategy_used: str | None = None
    fallback_from: str | None = None


@dataclass
class ExportOptions:
    container: str = "mp4"  # mp4 | mov | mkv
    codec: str = "h264"  # h264 | hevc
    quality: str = "balanced"  # fast | balanced | best
    target_width: int | None = None
    target_height: int | None = None
    preserve_hdr: bool = True
