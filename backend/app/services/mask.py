"""Selection mask persistence service."""

from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.mask import SelectionMask
from app.models.video import Video
from app.schemas.mask import (
    MaskCreateRequest,
    MaskOut,
    MaskSummaryOut,
    MaskUpdateRequest,
    SelectionPayload,
)


class MaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _summary(self, mask: SelectionMask) -> MaskSummaryOut:
        try:
            payload = json.loads(mask.payload_json)
            item_count = len(payload.get("items") or [])
        except json.JSONDecodeError:
            item_count = 0
        return MaskSummaryOut(
            id=mask.id,
            video_id=mask.video_id,
            name=mask.name,
            created_at=mask.created_at,
            updated_at=mask.updated_at,
            item_count=item_count,
        )

    def to_out(self, mask: SelectionMask) -> MaskOut:
        summary = self._summary(mask)
        payload = json.loads(mask.payload_json)
        return MaskOut(**summary.model_dump(), payload=payload)

    async def list_for_video(self, video: Video) -> tuple[list[MaskSummaryOut], int]:
        total = await self.db.scalar(
            select(func.count())
            .select_from(SelectionMask)
            .where(
                SelectionMask.video_id == video.id,
                SelectionMask.owner_id == video.owner_id,
            )
        )
        rows = await self.db.scalars(
            select(SelectionMask)
            .where(
                SelectionMask.video_id == video.id,
                SelectionMask.owner_id == video.owner_id,
            )
            .order_by(SelectionMask.updated_at.desc())
        )
        items = [self._summary(row) for row in rows]
        return items, int(total or 0)

    async def create(self, video: Video, request: MaskCreateRequest) -> MaskOut:
        mask = SelectionMask(
            video_id=video.id,
            owner_id=video.owner_id,
            name=request.name.strip(),
            payload_json=request.payload.model_dump_json(),
        )
        self.db.add(mask)
        await self.db.commit()
        await self.db.refresh(mask)
        return self.to_out(mask)

    async def get_owned(self, mask_id: str, owner_id: str) -> SelectionMask:
        mask = await self.db.scalar(
            select(SelectionMask).where(SelectionMask.id == mask_id)
        )
        if mask is None or mask.owner_id != owner_id:
            raise AppError(
                code="mask_not_found",
                message="Selection mask not found",
                status_code=404,
            )
        return mask

    async def update(
        self, mask: SelectionMask, request: MaskUpdateRequest
    ) -> MaskOut:
        if request.name is None and request.payload is None:
            raise AppError(
                code="validation_error",
                message="Provide a name and/or payload to update",
                status_code=422,
            )
        if request.name is not None:
            mask.name = request.name.strip()
        if request.payload is not None:
            SelectionPayload.model_validate(request.payload.model_dump())
            mask.payload_json = request.payload.model_dump_json()
        await self.db.commit()
        await self.db.refresh(mask)
        return self.to_out(mask)

    async def delete(self, mask: SelectionMask) -> None:
        await self.db.delete(mask)
        await self.db.commit()
