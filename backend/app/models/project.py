"""Project persistence — masks, settings, timeline, AI selections."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import Settings
from app.core.errors import AppError
from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    video_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def default_project_payload(video_id: str | None = None) -> dict[str, Any]:
    return {
        "version": 1,
        "video_id": video_id,
        "masks": [],
        "timeline": {"zoom": 1, "current_time": 0},
        "settings": {
            "feather": 12,
            "expansion": 0,
            "edge_refine": 2,
            "strategy": "ai_inpaint",
        },
        "ai_selections": [],
        "undo_stack": [],
        "redo_stack": [],
    }


class ProjectService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def projects_dir(self, owner_id: str) -> Path:
        path = Path(self.settings.storage_root) / "projects" / owner_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_sidecar(self, owner_id: str, project_id: str, payload: dict) -> Path:
        path = self.projects_dir(owner_id) / f"{project_id}.pavc.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
