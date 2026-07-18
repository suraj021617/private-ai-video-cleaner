"""Upload and progress schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class UploadInitRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)
    content_type: str = Field(min_length=3, max_length=128)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        name = value.strip().replace("\\", "/").split("/")[-1]
        if not name or name in {".", ".."}:
            raise ValueError("Invalid filename")
        if any(ch in name for ch in ["\x00", "\n", "\r"]):
            raise ValueError("Invalid filename characters")
        return name


class UploadInitResponse(BaseModel):
    id: str
    chunk_size: int
    chunks_total: int
    status: str


class UploadProgressResponse(BaseModel):
    id: str
    status: str
    bytes_received: int
    bytes_total: int
    chunks_received: int
    chunks_total: int
    percent: float
    video_id: str | None = None
    error: str | None = None
