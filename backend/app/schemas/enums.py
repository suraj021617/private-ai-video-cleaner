"""Domain enums reserved for later phases."""

from enum import Enum


class ProcessingStrategy(str, Enum):
    """Cleaning strategies. `ai_inpaint` is reserved for Phase 9."""

    BLUR = "blur"
    FILL = "fill"
    CLASSIC_INPAINT = "classic_inpaint"
    AI_INPAINT = "ai_inpaint"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
