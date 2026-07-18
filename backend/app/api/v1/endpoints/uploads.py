"""Upload and progress endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, require_auth
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.schemas.upload import (
    UploadInitRequest,
    UploadInitResponse,
    UploadProgressResponse,
)
from app.schemas.video import VideoOut
from app.services.upload import UploadService
from app.services.video import VideoService

router = APIRouter(prefix="/uploads", tags=["uploads"])


def get_upload_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadService:
    return UploadService(db, settings)


@router.post("", response_model=UploadInitResponse)
async def init_upload(
    payload: UploadInitRequest,
    auth: AuthContext = Depends(require_auth),
    service: UploadService = Depends(get_upload_service),
) -> UploadInitResponse:
    upload = await service.init_upload(
        owner_id=auth.user.id,
        filename=payload.filename,
        size_bytes=payload.size_bytes,
        content_type=payload.content_type,
    )
    return UploadInitResponse(
        id=upload.id,
        chunk_size=upload.chunk_size,
        chunks_total=upload.chunks_total,
        status=upload.status,
    )


@router.put("/{upload_id}/chunks/{chunk_index}", response_model=UploadProgressResponse)
async def upload_chunk(
    request: Request,
    upload_id: str,
    chunk_index: int = Path(ge=0),
    auth: AuthContext = Depends(require_auth),
    service: UploadService = Depends(get_upload_service),
    settings: Settings = Depends(get_settings),
) -> UploadProgressResponse:
    content_type = request.headers.get("content-type", "")
    if content_type and not content_type.startswith("application/octet-stream"):
        raise AppError(
            code="unsupported_media_type",
            message="Chunk uploads must use application/octet-stream",
            status_code=415,
        )

    body = await request.body()
    if len(body) > settings.upload_chunk_size:
        raise AppError(
            code="payload_too_large",
            message="Chunk exceeds configured chunk size",
            status_code=413,
        )

    upload = await service.get_owned_upload(upload_id, auth.user.id)
    upload = await service.save_chunk(upload, chunk_index=chunk_index, data=body)
    return UploadProgressResponse(**service.progress_payload(upload))


@router.post("/{upload_id}/complete", response_model=VideoOut)
async def complete_upload(
    upload_id: str,
    auth: AuthContext = Depends(require_auth),
    service: UploadService = Depends(get_upload_service),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> VideoOut:
    upload = await service.get_owned_upload(upload_id, auth.user.id)
    video = await service.complete(upload)
    return VideoService(db, settings).to_out(video)


@router.get("/{upload_id}/progress", response_model=UploadProgressResponse)
async def upload_progress(
    upload_id: str,
    auth: AuthContext = Depends(require_auth),
    service: UploadService = Depends(get_upload_service),
) -> UploadProgressResponse:
    upload = await service.get_owned_upload(upload_id, auth.user.id)
    return UploadProgressResponse(**service.progress_payload(upload))


@router.delete("/{upload_id}", status_code=204, response_model=None)
async def cancel_upload(
    upload_id: str,
    auth: AuthContext = Depends(require_auth),
    service: UploadService = Depends(get_upload_service),
) -> None:
    upload = await service.get_owned_upload(upload_id, auth.user.id)
    await service.cancel(upload)
