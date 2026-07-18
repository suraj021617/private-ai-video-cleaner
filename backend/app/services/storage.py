"""Storage path helpers and filesystem operations."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import Settings


class StorageService:
    """Per-user filesystem layout under storage_root."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def processed_dir(self) -> Path:
        return self.settings.processed_dir

    def ensure_roots(self) -> None:
        for path in (
            self.settings.uploads_dir,
            self.settings.processed_dir,
            self.settings.temp_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def user_upload_root(self, user_id: str) -> Path:
        path = self.settings.uploads_dir / user_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def upload_temp_dir(self, upload_id: str) -> Path:
        path = self.settings.temp_dir / "uploads" / upload_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def chunk_path(self, upload_id: str, chunk_index: int) -> Path:
        return self.upload_temp_dir(upload_id) / f"chunk_{chunk_index:06d}.part"

    def video_dir(self, user_id: str, video_id: str) -> Path:
        path = self.user_upload_root(user_id) / video_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def video_source_path(self, user_id: str, video_id: str, extension: str) -> Path:
        ext = extension.lower().lstrip(".")
        return self.video_dir(user_id, video_id) / f"source.{ext}"

    def remove_path(self, path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink(missing_ok=True)

    def resolve_under_storage(self, relative_or_absolute: str) -> Path:
        path = Path(relative_or_absolute)
        if not path.is_absolute():
            path = (self.settings.storage_root / path).resolve()
        else:
            path = path.resolve()
        root = self.settings.storage_root.resolve()
        if root not in path.parents and path != root:
            raise ValueError("Path escapes storage root")
        return path
