"""Domain enums — kept in sync with processing package."""

from enum import Enum


class ProcessingStrategy(str, Enum):
    BLUR = "blur"
    FILL = "fill"
    CLASSIC_INPAINT = "classic_inpaint"
    AI_INPAINT = "ai_inpaint"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
