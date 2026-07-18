"""Domain enums — kept in sync with processing package."""

from enum import Enum


class ProcessingStrategy(str, Enum):
    BLUR = "blur"
    FILL = "fill"
    CLASSIC_INPAINT = "classic_inpaint"
    AI_INPAINT = "ai_inpaint"
    PROPAINTER = "propainter"
    STTN = "sttn"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportCodec(str, Enum):
    H264 = "h264"
    HEVC = "hevc"


class ExportQuality(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    BEST = "best"
