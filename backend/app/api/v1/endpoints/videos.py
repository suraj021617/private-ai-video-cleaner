"""Video metadata and content endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, require_auth
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.schemas.video import VideoListResponse, VideoMetadataOut, VideoOut
from app.services.video import VideoService

router = APIRouter(prefix="/videos", tags=["videos"])


def get_video_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VideoService:
    return VideoService(db, settings)


@router.get("", response_model=VideoListResponse)
async def list_videos(
    auth: AuthContext = Depends(require_auth),
    service: VideoService = Depends(get_video_service),
) -> VideoListResponse:
    videos, total = await service.list_for_owner(auth.user.id)
    return VideoListResponse(
        items=[service.to_out(v) for v in videos],
        total=total,
    )


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(
    video_id: str,
    auth: AuthContext = Depends(require_auth),
    service: VideoService = Depends(get_video_service),
) -> VideoOut:
    video = await service.get_owned(video_id, auth.user.id)
    return service.to_out(video)


@router.get("/{video_id}/metadata", response_model=VideoMetadataOut)
async def get_video_metadata(
    video_id: str,
    auth: AuthContext = Depends(require_auth),
    service: VideoService = Depends(get_video_service),
) -> VideoMetadataOut:
    video = await service.get_owned(video_id, auth.user.id)
    return service.to_out(video).metadata


@router.get("/{video_id}/content")
async def stream_video_content(
    video_id: str,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    service: VideoService = Depends(get_video_service),
) -> Response:
    video = await service.get_owned(video_id, auth.user.id)
    path = Path(video.storage_path)
    if not path.is_file():
        raise AppError(
            code="file_missing",
            message="Video file is missing from storage",
            status_code=404,
        )

    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": video.content_type or "application/octet-stream",
        "Content-Disposition": f'inline; filename="{video.original_filename}"',
    }

    if not range_header:
        return FileResponse(
            path,
            media_type=video.content_type or "application/octet-stream",
            filename=video.original_filename,
            headers={"Accept-Ranges": "bytes"},
        )

    # bytes=start-end
    units, _, rng = range_header.partition("=")
    if units.strip() != "bytes" or not rng:
        raise AppError(
            code="invalid_range",
            message="Invalid Range header",
            status_code=416,
        )
    start_s, _, end_s = rng.partition("-")
    try:
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
    except ValueError as exc:
        raise AppError(
            code="invalid_range",
            message="Invalid Range header",
            status_code=416,
        ) from exc

    if start < 0 or end < start or start >= file_size:
        raise AppError(
            code="invalid_range",
            message="Requested range not satisfiable",
            status_code=416,
            details={"size": file_size},
        )
    end = min(end, file_size - 1)
    length = end - start + 1

    with path.open("rb") as handle:
        handle.seek(start)
        data = handle.read(length)

    headers.update(
        {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(length),
        }
    )
    return Response(content=data, status_code=206, headers=headers, media_type=video.content_type)


@router.delete("/{video_id}", status_code=204, response_model=None)
async def delete_video(
    video_id: str,
    auth: AuthContext = Depends(require_auth),
    service: VideoService = Depends(get_video_service),
) -> None:
    await service.delete_owned(video_id, auth.user.id)
