"""Health and readiness endpoints."""

import shutil
from pathlib import Path

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=__version__,
        phase="1-scaffold",
    )


@router.get("/ready", response_model=ReadinessResponse)
def ready() -> ReadinessResponse:
    """Lightweight dependency checks for local/ops use."""
    settings = get_settings()
    ffmpeg_available = shutil.which("ffmpeg") is not None

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

    status = "ready" if ffmpeg_available and storage_ok else "degraded"
    detail_parts: list[str] = []
    if not ffmpeg_available:
        detail_parts.append("ffmpeg not found on PATH")
    if not storage_ok:
        detail_parts.append("storage directories not writable")

    return ReadinessResponse(
        status=status,
        ffmpeg_available=ffmpeg_available,
        storage_writable=storage_ok,
        detail="; ".join(detail_parts) if detail_parts else None,
    )
