"""Selection mask endpoints for the video editor."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, require_auth
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.mask import (
    MaskCreateRequest,
    MaskListResponse,
    MaskOut,
    MaskUpdateRequest,
)
from app.services.mask import MaskService
from app.services.video import VideoService

router = APIRouter(tags=["masks"])


def get_video_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VideoService:
    return VideoService(db, settings)


def get_mask_service(db: AsyncSession = Depends(get_db)) -> MaskService:
    return MaskService(db)


@router.get("/videos/{video_id}/masks", response_model=MaskListResponse)
async def list_masks(
    video_id: str,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
    masks: MaskService = Depends(get_mask_service),
) -> MaskListResponse:
    video = await videos.get_owned(video_id, auth.user.id)
    items, total = await masks.list_for_video(video)
    return MaskListResponse(items=items, total=total)


@router.post("/videos/{video_id}/masks", response_model=MaskOut)
async def create_mask(
    video_id: str,
    payload: MaskCreateRequest,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
    masks: MaskService = Depends(get_mask_service),
) -> MaskOut:
    video = await videos.get_owned(video_id, auth.user.id)
    return await masks.create(video, payload)


@router.get("/videos/{video_id}/masks/{mask_id}", response_model=MaskOut)
async def get_mask(
    video_id: str,
    mask_id: str,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
    masks: MaskService = Depends(get_mask_service),
) -> MaskOut:
    await videos.get_owned(video_id, auth.user.id)
    mask = await masks.get_owned(mask_id, auth.user.id)
    if mask.video_id != video_id:
        from app.core.errors import AppError

        raise AppError(
            code="mask_not_found",
            message="Selection mask not found",
            status_code=404,
        )
    return masks.to_out(mask)


@router.put("/videos/{video_id}/masks/{mask_id}", response_model=MaskOut)
async def update_mask(
    video_id: str,
    mask_id: str,
    payload: MaskUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
    masks: MaskService = Depends(get_mask_service),
) -> MaskOut:
    await videos.get_owned(video_id, auth.user.id)
    mask = await masks.get_owned(mask_id, auth.user.id)
    if mask.video_id != video_id:
        from app.core.errors import AppError

        raise AppError(
            code="mask_not_found",
            message="Selection mask not found",
            status_code=404,
        )
    return await masks.update(mask, payload)


@router.delete("/videos/{video_id}/masks/{mask_id}", status_code=204, response_model=None)
async def delete_mask(
    video_id: str,
    mask_id: str,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
    masks: MaskService = Depends(get_mask_service),
) -> None:
    await videos.get_owned(video_id, auth.user.id)
    mask = await masks.get_owned(mask_id, auth.user.id)
    if mask.video_id != video_id:
        from app.core.errors import AppError

        raise AppError(
            code="mask_not_found",
            message="Selection mask not found",
            status_code=404,
        )
    await masks.delete(mask)
