"""Video query and deletion services."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.models.video import Video
from app.schemas.video import VideoMetadataOut, VideoOut
from app.services.storage import StorageService


class VideoService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.storage = StorageService(settings)

    def to_out(self, video: Video) -> VideoOut:
        return VideoOut(
            id=video.id,
            original_filename=video.original_filename,
            content_type=video.content_type,
            size_bytes=video.size_bytes,
            status=video.status,
            created_at=video.created_at,
            updated_at=video.updated_at,
            metadata=VideoMetadataOut(
                duration_seconds=video.duration_seconds,
                width=video.width,
                height=video.height,
                fps=video.fps,
                video_codec=video.video_codec,
                audio_codec=video.audio_codec,
                container=video.container,
                bitrate=video.bitrate,
            ),
        )

    async def list_for_owner(self, owner_id: str) -> tuple[list[Video], int]:
        total = await self.db.scalar(
            select(func.count())
            .select_from(Video)
            .where(Video.owner_id == owner_id)
        )
        result = await self.db.scalars(
            select(Video)
            .where(Video.owner_id == owner_id)
            .order_by(Video.created_at.desc())
        )
        return list(result), int(total or 0)

    async def get_owned(self, video_id: str, owner_id: str) -> Video:
        video = await self.db.scalar(select(Video).where(Video.id == video_id))
        if video is None or video.owner_id != owner_id:
            raise AppError(
                code="video_not_found",
                message="Video not found",
                status_code=404,
            )
        return video

    async def delete_owned(self, video_id: str, owner_id: str) -> None:
        video = await self.get_owned(video_id, owner_id)
        path = Path(video.storage_path)
        parent = path.parent if path.suffix else path
        await self.db.delete(video)
        await self.db.commit()
        if parent.exists() and parent.is_dir():
            self.storage.remove_path(parent)
        elif path.exists():
            self.storage.remove_path(path)
