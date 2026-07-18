"""Processing jobs API."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, require_auth
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.processing.device import benchmark_devices, device_capabilities, memory_status
from app.processing.plugins.lama import get_model_manager
from app.processing.strategies import list_strategies
from app.schemas.job import (
    DeviceInfoResponse,
    JobCreateRequest,
    JobOut,
    JobProgressOut,
    StrategyInfo,
)
from app.services.jobs import JobService, run_job_worker
from app.services.runtime_settings import apply_runtime_overrides
from app.services.video import VideoService

router = APIRouter(tags=["jobs"])


def get_video_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VideoService:
    return VideoService(db, settings)


def get_job_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JobService:
    return JobService(db, settings)


@router.get("/processing/capabilities", response_model=DeviceInfoResponse)
async def processing_capabilities(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> DeviceInfoResponse:
    caps = device_capabilities()
    effective = apply_runtime_overrides(settings)
    manager = get_model_manager(
        effective.lama_model_dir, prefer_gpu=effective.lama_prefer_gpu
    )
    return DeviceInfoResponse(
        cuda_devices=int(caps["cuda_devices"]),
        opencl_available=bool(caps["opencl_available"]),
        selected=str(caps["selected"]),
        strategies=[StrategyInfo(**item) for item in list_strategies()],
        lama=manager.status,
        gpu_benchmark=benchmark_devices(),
        memory=memory_status(),
    )


@router.post("/videos/{video_id}/jobs", response_model=JobOut)
async def create_job(
    video_id: str,
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
    jobs: JobService = Depends(get_job_service),
    settings: Settings = Depends(get_settings),
) -> JobOut:
    video = await videos.get_owned(video_id, auth.user.id)
    job = await jobs.create_job(
        video=video, owner_id=auth.user.id, request=payload
    )
    background_tasks.add_task(run_job_worker, job.id, settings)
    position = await jobs.queue_position(job)
    return jobs.to_out(job, queue_position=position)


@router.get("/videos/{video_id}/jobs", response_model=list[JobOut])
async def list_jobs(
    video_id: str,
    auth: AuthContext = Depends(require_auth),
    videos: VideoService = Depends(get_video_service),
    jobs: JobService = Depends(get_job_service),
) -> list[JobOut]:
    await videos.get_owned(video_id, auth.user.id)
    rows = await jobs.list_for_video(video_id, auth.user.id)
    out: list[JobOut] = []
    for row in rows:
        position = await jobs.queue_position(row)
        out.append(jobs.to_out(row, queue_position=position))
    return out


@router.get("/jobs", response_model=list[JobOut])
async def list_all_jobs(
    auth: AuthContext = Depends(require_auth),
    jobs: JobService = Depends(get_job_service),
) -> list[JobOut]:
    rows = await jobs.list_all(auth.user.id)
    out: list[JobOut] = []
    for row in rows:
        position = await jobs.queue_position(row)
        out.append(jobs.to_out(row, queue_position=position))
    return out


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    auth: AuthContext = Depends(require_auth),
    jobs: JobService = Depends(get_job_service),
) -> JobOut:
    job = await jobs.get_owned(job_id, auth.user.id)
    position = await jobs.queue_position(job)
    return jobs.to_out(job, queue_position=position)


@router.get("/jobs/{job_id}/progress", response_model=JobProgressOut)
async def job_progress(
    job_id: str,
    auth: AuthContext = Depends(require_auth),
    jobs: JobService = Depends(get_job_service),
) -> JobProgressOut:
    job = await jobs.get_owned(job_id, auth.user.id)
    position = await jobs.queue_position(job)
    return jobs.to_progress(job, queue_position=position)


@router.post("/jobs/{job_id}/pause", response_model=JobOut)
async def pause_job(
    job_id: str,
    auth: AuthContext = Depends(require_auth),
    jobs: JobService = Depends(get_job_service),
) -> JobOut:
    job = await jobs.get_owned(job_id, auth.user.id)
    job = await jobs.pause(job)
    return jobs.to_out(job)


@router.post("/jobs/{job_id}/resume", response_model=JobOut)
async def resume_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_auth),
    jobs: JobService = Depends(get_job_service),
    settings: Settings = Depends(get_settings),
) -> JobOut:
    job = await jobs.get_owned(job_id, auth.user.id)
    job = await jobs.resume(job)
    if job.status == "queued":
        background_tasks.add_task(run_job_worker, job.id, settings)
    return jobs.to_out(job)


@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
async def cancel_job(
    job_id: str,
    auth: AuthContext = Depends(require_auth),
    jobs: JobService = Depends(get_job_service),
) -> JobOut:
    job = await jobs.get_owned(job_id, auth.user.id)
    job = await jobs.cancel(job)
    return jobs.to_out(job)


@router.get("/jobs/{job_id}/download")
async def download_job_output(
    job_id: str,
    auth: AuthContext = Depends(require_auth),
    jobs: JobService = Depends(get_job_service),
) -> FileResponse:
    job = await jobs.get_owned(job_id, auth.user.id)
    if job.status != "completed" or not job.output_path:
        raise AppError(
            code="export_not_ready",
            message="Processed export is not ready",
            status_code=409,
            details={"status": job.status},
        )
    path = Path(job.output_path)
    if not path.is_file():
        raise AppError(
            code="export_missing",
            message="Processed file is missing from storage",
            status_code=404,
        )
    try:
        options = json.loads(job.options_json or "{}")
    except json.JSONDecodeError:
        options = {}
    fmt = str(options.get("export_format", path.suffix.lstrip(".") or "mp4"))
    media = {
        "mov": "video/quicktime",
        "mkv": "video/x-matroska",
        "mp4": "video/mp4",
    }.get(fmt, "application/octet-stream")
    return FileResponse(
        path,
        media_type=media,
        filename=f"processed-{job.id}.{fmt}",
    )
