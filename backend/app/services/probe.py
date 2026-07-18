"""ffprobe-based video metadata extraction (no encoding/processing)."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.errors import AppError


@dataclass(frozen=True)
class VideoProbeResult:
    duration_seconds: float | None
    width: int | None
    height: int | None
    fps: float | None
    video_codec: str | None
    audio_codec: str | None
    container: str | None
    bitrate: int | None


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def _parse_fps(raw: str | None) -> float | None:
    if not raw or raw in {"0/0", "N/A"}:
        return None
    if "/" in raw:
        num_s, den_s = raw.split("/", 1)
        try:
            num = float(num_s)
            den = float(den_s)
        except ValueError:
            return None
        if den == 0:
            return None
        return num / den
    try:
        return float(raw)
    except ValueError:
        return None


def probe_video(path: Path) -> VideoProbeResult:
    if not ffprobe_available():
        raise AppError(
            code="ffprobe_missing",
            message="ffprobe is required for video metadata extraction",
            status_code=503,
        )
    if not path.is_file():
        raise AppError(
            code="file_not_found",
            message="Video file not found for probing",
            status_code=404,
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-print_format",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise AppError(
            code="probe_timeout",
            message="Timed out while reading video metadata",
            status_code=504,
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise AppError(
            code="probe_failed",
            message="Unable to read video metadata. File may be corrupt or unsupported.",
            status_code=422,
            details={"stderr": (exc.stderr or "")[:500]},
        ) from exc

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AppError(
            code="probe_failed",
            message="Invalid ffprobe output",
            status_code=500,
        ) from exc

    format_info = payload.get("format") or {}
    streams = payload.get("streams") or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if video_stream is None:
        raise AppError(
            code="invalid_video",
            message="No video stream found in uploaded file",
            status_code=422,
        )

    duration = format_info.get("duration")
    bitrate = format_info.get("bit_rate")

    return VideoProbeResult(
        duration_seconds=float(duration) if duration is not None else None,
        width=int(video_stream["width"]) if video_stream.get("width") else None,
        height=int(video_stream["height"]) if video_stream.get("height") else None,
        fps=_parse_fps(video_stream.get("avg_frame_rate")),
        video_codec=video_stream.get("codec_name"),
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        container=format_info.get("format_name"),
        bitrate=int(bitrate) if bitrate is not None else None,
    )
