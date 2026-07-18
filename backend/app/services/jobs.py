"""Job orchestration: create, queue, pause/resume/cancel, recover, report progress."""

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
from app.processing.types import ExportOptions, PipelineProgress, StrategyOptions
from app.schemas.job import JobCreateRequest, JobOut, JobProgressOut
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

# In-process concurrency gate (one worker process).
_active_job_ids: set[str] = set()
_MAX_CONCURRENT_DEFAULT = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _options_dict(job: ProcessingJob) -> dict:
    try:
        return json.loads(job.options_json or "{}")
    except json.JSONDecodeError:
        return {}


class JobService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.storage = StorageService(settings)

    async def queue_position(self, job: ProcessingJob) -> int | None:
        if job.status != "queued":
            return None
        rows = await self.db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.status == "queued")
            .order_by(ProcessingJob.created_at.asc())
        )
        for idx, row in enumerate(rows, start=1):
            if row.id == job.id:
                return idx
        return None

    def to_out(self, job: ProcessingJob, queue_position: int | None = None) -> JobOut:
        options = _options_dict(job)
        return JobOut(
            id=job.id,
            video_id=job.video_id,
            mask_id=job.mask_id,
            strategy=job.strategy,
            strategy_used=job.strategy_used,
            status=job.status,
            prefer_gpu=bool(job.prefer_gpu),
            device_used=job.device_used,
            frames_total=job.frames_total,
            frames_done=job.frames_done,
            percent=job.percent,
            message=job.message,
            error_message=job.error_message,
            download_ready=job.status == "completed" and bool(job.output_path),
            export_format=str(options.get("export_format", "mp4")),
            export_codec=str(options.get("export_codec", "h264")),
            export_quality=str(options.get("export_quality", "balanced")),
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
            queue_position=queue_position,
        )

    def to_progress(
        self, job: ProcessingJob, queue_position: int | None = None
    ) -> JobProgressOut:
        options = _options_dict(job)
        metrics = options.get("_progress") or {}
        error_reason = None
        suggested_fix = None
        if job.status == "failed" and job.error_message:
            from app.services.diagnostics import explain_error

            help_ = explain_error(job.error_message)
            error_reason = help_["reason"]
            suggested_fix = help_["suggested_fix"]
        return JobProgressOut(
            id=job.id,
            status=job.status,
            frames_total=job.frames_total,
            frames_done=job.frames_done,
            percent=job.percent,
            message=job.message,
            device_used=job.device_used,
            error=job.error_message,
            fps=metrics.get("fps"),
            eta_seconds=metrics.get("eta_seconds"),
            model_loaded=metrics.get("model_loaded"),
            strategy_used=job.strategy_used or metrics.get("strategy_used"),
            fallback_from=metrics.get("fallback_from"),
            queue_position=queue_position,
            error_reason=error_reason,
            suggested_fix=suggested_fix,
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

        # Apply job-level polish defaults onto payload without wiping caller values
        if request.feather_radius and not payload.get("feather"):
            payload["feather"] = request.feather_radius
        if request.mask_expansion and not payload.get("expansion"):
            payload["expansion"] = request.mask_expansion
        if request.edge_refine and not payload.get("edge_refine"):
            payload["edge_refine"] = request.edge_refine

        has_items = bool(payload.get("items"))
        has_masks = any(
            (group.get("items") or []) for group in (payload.get("masks") or [])
        )
        if not has_items and not has_masks:
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
            "export_format": request.export_format,
            "export_codec": request.export_codec,
            "export_quality": request.export_quality,
            "export_width": request.export_width,
            "export_height": request.export_height,
            "padding": request.padding,
            "blend_strength": request.blend_strength,
            "feather_radius": request.feather_radius,
            "mask_expansion": request.mask_expansion,
            "edge_refine": request.edge_refine,
            "prefer_gpu": request.prefer_gpu,
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
            cancel_requested=False,
            pause_requested=False,
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

    async def list_all(self, owner_id: str) -> list[ProcessingJob]:
        rows = await self.db.scalars(
            select(ProcessingJob)
            .where(ProcessingJob.owner_id == owner_id)
            .order_by(ProcessingJob.created_at.desc())
        )
        return list(rows)

    async def pause(self, job: ProcessingJob) -> ProcessingJob:
        if job.status not in {"queued", "running", "paused"}:
            raise AppError(
                code="job_not_pausable",
                message=f"Cannot pause job in status '{job.status}'",
                status_code=409,
            )
        job.pause_requested = True
        if job.status == "queued":
            job.status = "paused"
            job.message = "Paused (queue)"
        else:
            job.message = "Pause requested"
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def resume(self, job: ProcessingJob) -> ProcessingJob:
        if job.status not in {"paused", "running"} and not job.pause_requested:
            raise AppError(
                code="job_not_resumable",
                message=f"Cannot resume job in status '{job.status}'",
                status_code=409,
            )
        job.pause_requested = False
        if job.status == "paused":
            # Mid-flight pause keeps the worker alive; otherwise re-queue.
            if job.id in _active_job_ids or job.frames_done > 0:
                job.status = "running"
                job.message = "Resumed"
            else:
                job.status = "queued"
                job.message = "Resumed — queued"
        else:
            job.message = "Resumed"
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def cancel(self, job: ProcessingJob) -> ProcessingJob:
        if job.status in {"completed", "failed", "cancelled"}:
            raise AppError(
                code="job_not_cancellable",
                message=f"Cannot cancel job in status '{job.status}'",
                status_code=409,
            )
        job.cancel_requested = True
        if job.status in {"queued", "paused"}:
            job.status = "cancelled"
            job.message = "Cancelled"
            job.error_message = None
            job.completed_at = _utcnow()
        else:
            job.message = "Cancel requested"
        await self.db.commit()
        await self.db.refresh(job)
        return job


async def recover_interrupted_jobs(settings: Settings) -> list[str]:
    """
    On startup, re-queue jobs left in 'running' after a crash.
    Returns recovered job ids.
    """
    from app.db.session import get_session_factory

    factory = get_session_factory()
    recovered: list[str] = []
    async with factory() as db:
        rows = await db.scalars(
            select(ProcessingJob).where(ProcessingJob.status == "running")
        )
        for job in rows:
            if job.cancel_requested:
                job.status = "cancelled"
                job.message = "Cancelled during recovery"
                job.completed_at = _utcnow()
            else:
                job.status = "queued"
                job.message = "Recovered after restart — queued"
                job.pause_requested = False
                recovered.append(job.id)
        await db.commit()
    return recovered


async def run_job_worker(job_id: str, settings: Settings) -> None:
    """Execute a job in a background task with its own DB session."""
    from app.db.session import get_session_factory
    from app.services.runtime_settings import apply_runtime_overrides

    settings = apply_runtime_overrides(settings)
    max_concurrent = getattr(settings, "max_concurrent_jobs", _MAX_CONCURRENT_DEFAULT)
    # Simple wait if at capacity
    while len(_active_job_ids) >= max_concurrent and job_id not in _active_job_ids:
        await asyncio.sleep(0.5)

    factory = get_session_factory()
    async with factory() as db:
        job = await db.scalar(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        if job is None:
            return
        if job.cancel_requested or job.status == "cancelled":
            job.status = "cancelled"
            job.message = "Cancelled"
            await db.commit()
            return
        if job.status == "paused" or job.pause_requested:
            job.status = "paused"
            job.message = "Paused"
            await db.commit()
            return
        if job.status not in {"queued", "running"}:
            return

        video = await db.scalar(select(Video).where(Video.id == job.video_id))
        if video is None:
            job.status = "failed"
            job.error_message = "Source video missing"
            await db.commit()
            return

        storage = StorageService(settings)
        prefer_gpu = bool(job.prefer_gpu)
        strategy_name = job.strategy
        mask_payload_raw = job.mask_payload_json
        options_data = json.loads(job.options_json or "{}")
        export_format = str(options_data.get("export_format", "mp4"))
        if export_format not in {"mp4", "mov", "mkv"}:
            export_format = "mp4"
        source = Path(video.storage_path)
        work_dir = settings.temp_dir / "jobs" / job.id
        output_path = (
            storage.processed_dir / job.owner_id / f"{job.id}.{export_format}"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        job.status = "running"
        job.message = "Starting pipeline"
        await db.commit()

    _active_job_ids.add(job_id)
    try:
        if settings.lama_cpu_threads and settings.lama_cpu_threads > 0:
            try:
                import torch

                torch.set_num_threads(int(settings.lama_cpu_threads))
            except Exception:  # noqa: BLE001
                pass

        options = StrategyOptions(
            blur_ksize=int(options_data.get("blur_ksize", 31)),
            fill_color_bgr=tuple(options_data.get("fill_color_bgr", [0, 0, 0])),  # type: ignore[arg-type]
            inpaint_radius=int(options_data.get("inpaint_radius", 3)),
            inpaint_method=str(options_data.get("inpaint_method", "telea")),
            extras={
                "model_dir": str(settings.lama_model_dir),
                "prefer_gpu": prefer_gpu,
                "padding": int(options_data.get("padding", settings.lama_padding)),
                "blend_strength": float(
                    options_data.get("blend_strength", settings.lama_blend_strength)
                ),
                "feather_radius": int(
                    options_data.get("feather_radius", settings.lama_feather_radius)
                ),
            },
        )
        export_options = ExportOptions(
            container=export_format,
            codec=str(options_data.get("export_codec", "h264")),
            quality=str(options_data.get("export_quality", "balanced")),
            target_width=options_data.get("export_width"),
            target_height=options_data.get("export_height"),
            preserve_hdr=True,
        )
        payload = json.loads(mask_payload_raw)
        pipeline = VideoProcessingPipeline(
            prefer_gpu=prefer_gpu,
            strategy_options=options,
            export_format=export_format,
            export_options=export_options,
        )

        loop = asyncio.get_running_loop()
        last_commit = 0.0
        control_cache = {"signal": None, "checked": 0.0}

        def on_control() -> str | None:
            now = loop.time()
            if now - control_cache["checked"] < 0.2:
                return control_cache["signal"]  # type: ignore[return-value]
            control_cache["checked"] = now

            async def _read() -> str | None:
                async with factory() as control_db:
                    row = await control_db.scalar(
                        select(ProcessingJob).where(ProcessingJob.id == job_id)
                    )
                    if row is None:
                        return "cancel"
                    if row.cancel_requested:
                        return "cancel"
                    if row.pause_requested:
                        if row.status != "paused":
                            row.status = "paused"
                            row.message = "Paused"
                            await control_db.commit()
                        return "pause"
                    return None

            future = asyncio.run_coroutine_threadsafe(_read(), loop)
            try:
                signal = future.result(timeout=2.0)
            except Exception:  # noqa: BLE001
                signal = None
            control_cache["signal"] = signal
            return signal

        def on_progress(progress: PipelineProgress) -> None:
            nonlocal last_commit

            async def _update() -> None:
                async with factory() as progress_db:
                    row = await progress_db.scalar(
                        select(ProcessingJob).where(ProcessingJob.id == job_id)
                    )
                    if row is None:
                        return
                    if row.cancel_requested:
                        return
                    if row.pause_requested:
                        row.status = "paused"
                    else:
                        row.status = (
                            progress.status
                            if progress.status != "encoding"
                            else "running"
                        )
                    row.frames_total = progress.frames_total
                    row.frames_done = progress.frames_done
                    row.percent = progress.percent
                    row.message = progress.message
                    row.device_used = progress.device
                    if progress.strategy_used:
                        row.strategy_used = progress.strategy_used
                    opts = _options_dict(row)
                    opts["_progress"] = {
                        "fps": progress.fps,
                        "eta_seconds": progress.eta_seconds,
                        "model_loaded": progress.model_loaded,
                        "strategy_used": progress.strategy_used,
                        "fallback_from": progress.fallback_from,
                    }
                    row.options_json = json.dumps(opts)
                    await progress_db.commit()

            now = loop.time()
            if (
                progress.percent >= 100
                or progress.status in {"encoding", "completed"}
                or now - last_commit >= 0.4
            ):
                last_commit = now
                asyncio.run_coroutine_threadsafe(_update(), loop)

        try:
            result = await asyncio.to_thread(
                pipeline.run,
                source_path=source,
                output_path=output_path,
                work_dir=work_dir,
                strategy=strategy_name,
                mask_payload=payload,
                on_progress=on_progress,
                on_control=on_control,
            )
            async with factory() as done_db:
                row = await done_db.scalar(
                    select(ProcessingJob).where(ProcessingJob.id == job_id)
                )
                if row is None:
                    return
                if row.cancel_requested:
                    row.status = "cancelled"
                    row.message = "Cancelled"
                    row.completed_at = _utcnow()
                    await done_db.commit()
                    return
                row.status = "completed"
                row.percent = 100.0
                row.frames_done = int(result["frames_processed"])
                row.frames_total = int(result["frames_processed"])
                row.device_used = str(result["device"])
                row.strategy_used = str(result.get("strategy") or row.strategy)
                row.output_path = str(result["output_path"])
                row.message = "Processing complete"
                row.error_message = None
                row.completed_at = _utcnow()
                await done_db.commit()
        except AppError as exc:
            async with factory() as err_db:
                row = await err_db.scalar(
                    select(ProcessingJob).where(ProcessingJob.id == job_id)
                )
                if row is None:
                    return
                if exc.code == "job_cancelled" or row.cancel_requested:
                    row.status = "cancelled"
                    row.message = "Cancelled"
                    row.error_message = None
                    row.completed_at = _utcnow()
                else:
                    logger.warning("Job %s failed: %s", job_id, exc.message)
                    row.status = "failed"
                    row.error_message = exc.message
                    row.message = "Failed"
                await err_db.commit()
        except Exception:  # noqa: BLE001
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
        finally:
            cleanup_work_dir(work_dir)
    finally:
        _active_job_ids.discard(job_id)
