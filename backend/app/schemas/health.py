"""Health / readiness response schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    service: str
    version: str
    phase: str = Field(
        description="Current product build phase label",
        examples=["1-scaffold"],
    )


class ReadinessResponse(BaseModel):
    status: str = Field(examples=["ready"])
    ffmpeg_available: bool
    storage_writable: bool
    detail: str | None = None
