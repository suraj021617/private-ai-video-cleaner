"""Job orchestration: create, run pipeline in a worker thread, report progress."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.models.job import ProcessingJob
from app.models.mask import SelectionMask
from app.models.video import Video
from app.processing.pipeline import VideoProcessingPipeline, cleanup_work_dir
from app.processing.types import PipelineProgress, StrategyOptions
from app.schemas.job import JobCreateRequest, JobOut, JobProgressOut
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.storage = StorageService(settings)

    def to_out(self, job: ProcessingJob) -> JobOut:
        return JobOut(
            id=job.id,
            video_id=job.video_id,
            mask_id=job.mask_id,
            strategy=job.strategy,
            status=job.status,
            prefer_gpu=bool(job.prefer_gpu),
            device_used=job.device_used,
            frames_total=job.frames_total,
            frames_done=job.frames_done,
            percent=job.percent,
            message=job.message,
            error_message=job.error_message,
            download_ready=job.status == "completed" and bool(job.output_path),
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
        )

    def to_progress(self, job: ProcessingJob) -> JobProgressOut:
        return JobProgressOut(
            id=job.id,
            status=job.status,
            frames_total=job.frames_total,
            frames_done=job.frames_done,
            percent=job.percent,
            message=job.message,
            device_used=job.device_used,
            error=job.error_message,
        )

    async def resolve_mask_payload(
        self, *, video: Video, request: JobCreateRequest, owner_id: str
    ) -> tuple[str | None, dict]:
        mask_id = request.mask_id
        if mask_id:
            mask = await self.db.scalar(
                select(SelectionMask).where(SelectionMask.id == mask_id)
            )
            if (
                mask is None
                or mask.owner_id != owner_id
                or mask.video_id != video.id
            ):
                raise AppError(
                    code="mask_not_found",
                    message="Selection mask not found for this video",
                    status_code=404,
                )

        # Prefer inlined payload (current editor state); fall back to saved mask.
        if request.payload is not None:
            payload = request.payload.model_dump()
        elif mask_id:
            mask = await self.db.scalar(
                select(SelectionMask).where(SelectionMask.id == mask_id)
            )
            assert mask is not None
            payload = json.loads(mask.payload_json)
        else:
            raise AppError(
                code="mask_required",
                message="Provide mask_id or payload",
                status_code=422,
            )

        if not payload.get("items"):
            raise AppError(
                code="empty_mask",
                message="Selection has no regions to process",
                status_code=422,
            )
        return mask_id, payload

    async def create_job(
        self, *, video: Video, owner_id: str, request: JobCreateRequest
    ) -> ProcessingJob:
        mask_id, payload = await self.resolve_mask_payload(
            video=video, request=request, owner_id=owner_id
        )
        options = {
            "blur_ksize": request.blur_ksize,
            "fill_color_bgr": list(request.fill_color_bgr),
            "inpaint_radius": request.inpaint_radius,
            "inpaint_method": request.inpaint_method,
        }
        job = ProcessingJob(
            owner_id=owner_id,
            video_id=video.id,
            mask_id=mask_id,
            strategy=request.strategy,
            status="queued",
            prefer_gpu=request.prefer_gpu,
            options_json=json.dumps(options),
            mask_payload_json=json.dumps(payload),
            message="Queued",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_owned(self, job_id: str, owner_id: str) -> ProcessingJob:
        job = await self.db.scalar(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        if job is None or job.owner_id != owner_id:
            raise AppError(
                code="job_not_found",
                message="Processing job not found",
                status_code=404,
            )
        return job

    async def list_for_video(
        self, video_id: str, owner_id: str
    ) -> list[ProcessingJob]:
        rows = await self.db.scalars(
            select(ProcessingJob)
            .where(
                ProcessingJob.video_id == video_id,
                ProcessingJob.owner_id == owner_id,
            )
            .order_by(ProcessingJob.created_at.desc())
        )
        return list(rows)


async def run_job_worker(job_id: str, settings: Settings) -> None:
    """Execute a job in a background task with its own DB session."""
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as db:
        job = await db.scalar(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        if job is None:
            return
        video = await db.scalar(select(Video).where(Video.id == job.video_id))
        if video is None:
            job.status = "failed"
            job.error_message = "Source video missing"
            await db.commit()
            return

        storage = StorageService(settings)
        source = Path(video.storage_path)
        work_dir = settings.temp_dir / "jobs" / job.id
        output_path = (
            storage.processed_dir / job.owner_id / f"{job.id}.mp4"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        job.status = "running"
        job.message = "Starting pipeline"
        await db.commit()

        options_data = json.loads(job.options_json or "{}")
        options = StrategyOptions(
            blur_ksize=int(options_data.get("blur_ksize", 31)),
            fill_color_bgr=tuple(options_data.get("fill_color_bgr", [0, 0, 0])),  # type: ignore[arg-type]
            inpaint_radius=int(options_data.get("inpaint_radius", 3)),
            inpaint_method=str(options_data.get("inpaint_method", "telea")),
        )
        payload = json.loads(job.mask_payload_json)
        pipeline = VideoProcessingPipeline(
            prefer_gpu=bool(job.prefer_gpu),
            strategy_options=options,
        )

        loop = asyncio.get_running_loop()
        last_commit = 0.0

        def on_progress(progress: PipelineProgress) -> None:
            nonlocal last_commit

            async def _update() -> None:
                nonlocal last_commit
                async with factory() as progress_db:
                    row = await progress_db.scalar(
                        select(ProcessingJob).where(ProcessingJob.id == job_id)
                    )
                    if row is None:
                        return
                    row.status = progress.status if progress.status != "encoding" else "running"
                    row.frames_total = progress.frames_total
                    row.frames_done = progress.frames_done
                    row.percent = progress.percent
                    row.message = progress.message
                    row.device_used = progress.device
                    await progress_db.commit()

            # Throttle DB writes from the worker thread via the event loop.
            now = loop.time()
            if progress.percent >= 100 or progress.status in {"encoding", "completed"} or now - last_commit >= 0.4:
                last_commit = now
                asyncio.run_coroutine_threadsafe(_update(), loop)

        try:
            result = await asyncio.to_thread(
                pipeline.run,
                source_path=source,
                output_path=output_path,
                work_dir=work_dir,
                strategy=job.strategy,
                mask_payload=payload,
                on_progress=on_progress,
            )
            async with factory() as done_db:
                row = await done_db.scalar(
                    select(ProcessingJob).where(ProcessingJob.id == job_id)
                )
                if row is None:
                    return
                row.status = "completed"
                row.percent = 100.0
                row.frames_done = int(result["frames_processed"])
                row.frames_total = int(result["frames_processed"])
                row.device_used = str(result["device"])
                row.output_path = str(result["output_path"])
                row.message = "Processing complete"
                row.error_message = None
                row.completed_at = _utcnow()
                await done_db.commit()
        except AppError as exc:
            logger.warning("Job %s failed: %s", job_id, exc.message)
            async with factory() as err_db:
                row = await err_db.scalar(
                    select(ProcessingJob).where(ProcessingJob.id == job_id)
                )
                if row:
                    row.status = "failed"
                    row.error_message = exc.message
                    row.message = "Failed"
                    await err_db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Job %s crashed", job_id)
            async with factory() as err_db:
                row = await err_db.scalar(
                    select(ProcessingJob).where(ProcessingJob.id == job_id)
                )
                if row:
                    row.status = "failed"
                    row.error_message = "Processing failed unexpectedly"
                    row.message = "Failed"
                    await err_db.commit()
            raise
        finally:
            cleanup_work_dir(work_dir)
