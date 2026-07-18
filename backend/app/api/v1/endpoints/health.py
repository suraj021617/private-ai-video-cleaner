"""Health and readiness endpoints."""

import shutil
from pathlib import Path

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services.probe import ffprobe_available

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=__version__,
        phase="6-7-production",
    )


@router.get("/ready", response_model=ReadinessResponse)
def ready() -> ReadinessResponse:
    settings = get_settings()
    ffmpeg_available = shutil.which("ffmpeg") is not None
    probe_ok = ffprobe_available()

    storage_ok = True
    for directory in (
        settings.uploads_dir,
        settings.processed_dir,
        settings.temp_dir,
    ):
        try:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError:
            storage_ok = False
            break

    ready_ok = ffmpeg_available and probe_ok and storage_ok
    status = "ready" if ready_ok else "degraded"
    detail_parts: list[str] = []
    if not ffmpeg_available:
        detail_parts.append("ffmpeg not found on PATH")
    if not probe_ok:
        detail_parts.append("ffprobe not found on PATH")
    if not storage_ok:
        detail_parts.append("storage directories not writable")

    return ReadinessResponse(
        status=status,
        ffmpeg_available=ffmpeg_available and probe_ok,
        storage_writable=storage_ok,
        detail="; ".join(detail_parts) if detail_parts else None,
    )
