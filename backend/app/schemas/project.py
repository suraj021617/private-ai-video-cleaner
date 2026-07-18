"""Project persistence schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    video_id: str | None = None
    payload: dict[str, Any] | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    video_id: str | None = None
    payload: dict[str, Any] | None = None


class ProjectSummaryOut(BaseModel):
    id: str
    name: str
    video_id: str | None
    created_at: datetime
    updated_at: datetime


class ProjectOut(ProjectSummaryOut):
    payload: dict[str, Any]


class ProjectListResponse(BaseModel):
    items: list[ProjectSummaryOut]
    total: int
