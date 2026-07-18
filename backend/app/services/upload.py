"""Chunked upload orchestration with progress tracking."""

from __future__ import annotations

import math
from pathlib import Path

import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.models.upload import Upload
from app.models.video import Video
from app.services.probe import probe_video
from app.services.storage import StorageService


class UploadService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.storage = StorageService(settings)

    def _extension(self, filename: str) -> str:
        return Path(filename).suffix.lower().lstrip(".")

    def _validate_declaration(
        self, *, filename: str, size_bytes: int, content_type: str
    ) -> str:
        ext = self._extension(filename)
        if ext not in self.settings.extension_allowlist:
            raise AppError(
                code="unsupported_extension",
                message=f"File extension .{ext or '?'} is not allowed",
                status_code=415,
                details={"allowed_extensions": sorted(self.settings.extension_allowlist)},
            )
        mime = content_type.lower().split(";")[0].strip()
        if mime not in self.settings.mime_allowlist:
            raise AppError(
                code="unsupported_media_type",
                message=f"Content type {mime} is not allowed",
                status_code=415,
                details={"allowed_mime_types": sorted(self.settings.mime_allowlist)},
            )
        if size_bytes > self.settings.max_upload_bytes:
            raise AppError(
                code="payload_too_large",
                message="File exceeds maximum upload size",
                status_code=413,
                details={"max_upload_bytes": self.settings.max_upload_bytes},
            )
        return ext

    async def init_upload(
        self,
        *,
        owner_id: str,
        filename: str,
        size_bytes: int,
        content_type: str,
    ) -> Upload:
        self._validate_declaration(
            filename=filename, size_bytes=size_bytes, content_type=content_type
        )
        chunk_size = self.settings.upload_chunk_size
        chunks_total = max(1, math.ceil(size_bytes / chunk_size))
        upload = Upload(
            owner_id=owner_id,
            original_filename=filename,
            content_type=content_type.lower().split(";")[0].strip(),
            size_bytes=size_bytes,
            chunk_size=chunk_size,
            chunks_total=chunks_total,
            chunks_received=0,
            bytes_received=0,
            status="initialized",
            temp_dir="",
        )
        self.db.add(upload)
        await self.db.flush()
        temp_dir = self.storage.upload_temp_dir(upload.id)
        upload.temp_dir = str(temp_dir)
        await self.db.commit()
        await self.db.refresh(upload)
        return upload

    async def get_owned_upload(self, upload_id: str, owner_id: str) -> Upload:
        upload = await self.db.scalar(select(Upload).where(Upload.id == upload_id))
        if upload is None or upload.owner_id != owner_id:
            raise AppError(
                code="upload_not_found",
                message="Upload not found",
                status_code=404,
            )
        return upload

    async def save_chunk(
        self,
        upload: Upload,
        *,
        chunk_index: int,
        data: bytes,
    ) -> Upload:
        if upload.status in {"completed", "failed", "cancelled", "probing", "assembling", "validating"}:
            raise AppError(
                code="upload_not_accepting_chunks",
                message=f"Upload is not accepting chunks (status={upload.status})",
                status_code=409,
            )
        if chunk_index < 0 or chunk_index >= upload.chunks_total:
            raise AppError(
                code="invalid_chunk_index",
                message="Chunk index out of range",
                status_code=400,
                details={"chunks_total": upload.chunks_total},
            )

        expected_max = upload.chunk_size
        is_last = chunk_index == upload.chunks_total - 1
        if is_last:
            remainder = upload.size_bytes % upload.chunk_size
            expected_max = remainder or upload.chunk_size
        if len(data) == 0 or len(data) > expected_max:
            raise AppError(
                code="invalid_chunk_size",
                message="Chunk size is invalid for this index",
                status_code=400,
                details={"expected_max": expected_max, "received": len(data)},
            )

        path = self.storage.chunk_path(upload.id, chunk_index)
        already_existed = path.exists()
        async with aiofiles.open(path, "wb") as handle:
            await handle.write(data)

        if not already_existed:
            upload.chunks_received += 1
            upload.bytes_received += len(data)
        else:
            # Replacing a chunk: recompute bytes from disk for accuracy
            total = 0
            for index in range(upload.chunks_total):
                part = self.storage.chunk_path(upload.id, index)
                if part.exists():
                    total += part.stat().st_size
            upload.bytes_received = total
            upload.chunks_received = sum(
                1
                for index in range(upload.chunks_total)
                if self.storage.chunk_path(upload.id, index).exists()
            )

        upload.status = "uploading"
        upload.error_message = None
        await self.db.commit()
        await self.db.refresh(upload)
        return upload

    def progress_payload(self, upload: Upload) -> dict:
        percent = 0.0
        if upload.size_bytes > 0:
            percent = min(100.0, round((upload.bytes_received / upload.size_bytes) * 100, 2))
        if upload.status == "completed":
            percent = 100.0
        return {
            "id": upload.id,
            "status": upload.status,
            "bytes_received": upload.bytes_received,
            "bytes_total": upload.size_bytes,
            "chunks_received": upload.chunks_received,
            "chunks_total": upload.chunks_total,
            "percent": percent,
            "video_id": upload.video_id,
            "error": upload.error_message,
        }

    async def complete(self, upload: Upload) -> Video:
        if upload.status == "completed" and upload.video_id:
            video = await self.db.scalar(select(Video).where(Video.id == upload.video_id))
            if video:
                return video

        if upload.chunks_received != upload.chunks_total:
            raise AppError(
                code="upload_incomplete",
                message="Not all chunks have been uploaded",
                status_code=409,
                details={
                    "chunks_received": upload.chunks_received,
                    "chunks_total": upload.chunks_total,
                },
            )

        try:
            upload.status = "assembling"
            await self.db.commit()

            ext = self._extension(upload.original_filename)
            assembled = self.storage.upload_temp_dir(upload.id) / f"assembled.{ext}"
            async with aiofiles.open(assembled, "wb") as out:
                for index in range(upload.chunks_total):
                    part = self.storage.chunk_path(upload.id, index)
                    if not part.exists():
                        raise AppError(
                            code="missing_chunk",
                            message=f"Missing chunk {index}",
                            status_code=409,
                        )
                    async with aiofiles.open(part, "rb") as handle:
                        while True:
                            block = await handle.read(1024 * 1024)
                            if not block:
                                break
                            await out.write(block)

            actual_size = assembled.stat().st_size
            if actual_size != upload.size_bytes:
                raise AppError(
                    code="size_mismatch",
                    message="Assembled file size does not match declared size",
                    status_code=400,
                    details={
                        "declared": upload.size_bytes,
                        "actual": actual_size,
                    },
                )

            upload.status = "validating"
            await self.db.commit()
            self._validate_declaration(
                filename=upload.original_filename,
                size_bytes=actual_size,
                content_type=upload.content_type,
            )

            video = Video(
                owner_id=upload.owner_id,
                original_filename=upload.original_filename,
                content_type=upload.content_type,
                size_bytes=actual_size,
                storage_path="",
                status="processing_metadata",
            )
            self.db.add(video)
            await self.db.flush()

            final_path = self.storage.video_source_path(
                upload.owner_id, video.id, ext
            )
            assembled.replace(final_path)
            video.storage_path = str(final_path)

            upload.status = "probing"
            await self.db.commit()

            meta = probe_video(final_path)
            video.duration_seconds = meta.duration_seconds
            video.width = meta.width
            video.height = meta.height
            video.fps = meta.fps
            video.video_codec = meta.video_codec
            video.audio_codec = meta.audio_codec
            video.container = meta.container
            video.bitrate = meta.bitrate
            video.status = "ready"

            upload.video_id = video.id
            upload.status = "completed"
            upload.error_message = None
            await self.db.commit()
            await self.db.refresh(video)

            # Cleanup chunk parts (keep final video)
            self.storage.remove_path(self.storage.upload_temp_dir(upload.id))
            return video
        except AppError as exc:
            upload.status = "failed"
            upload.error_message = exc.message
            await self.db.commit()
            raise
        except Exception as exc:  # noqa: BLE001
            upload.status = "failed"
            upload.error_message = "Upload completion failed"
            await self.db.commit()
            raise AppError(
                code="upload_complete_failed",
                message="Upload completion failed",
                status_code=500,
            ) from exc

    async def cancel(self, upload: Upload) -> None:
        if upload.status == "completed":
            raise AppError(
                code="upload_already_completed",
                message="Completed uploads cannot be cancelled",
                status_code=409,
            )
        upload.status = "cancelled"
        await self.db.commit()
        self.storage.remove_path(Path(upload.temp_dir))
