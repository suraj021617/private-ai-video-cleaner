"""FFmpeg-backed decode/encode helpers preserving fps, resolution, and audio."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

import cv2

from app.core.errors import AppError
from app.processing.types import VideoStreamInfo
from app.services.probe import probe_video

logger = logging.getLogger(__name__)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def probe_stream(path: Path) -> VideoStreamInfo:
    meta = probe_video(path)
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise AppError(
            code="video_open_failed",
            message="Unable to open video for processing",
            status_code=422,
        )
    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or meta.width or 0
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or meta.height or 0
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or float(meta.fps or 0.0) or 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = float(meta.duration_seconds or 0.0)
        if duration <= 0 and fps > 0 and frame_count > 0:
            duration = frame_count / fps
    finally:
        cap.release()

    has_audio = _has_audio_stream(path)
    return VideoStreamInfo(
        width=width,
        height=height,
        fps=fps,
        frame_count=frame_count,
        duration_seconds=duration,
        has_audio=has_audio,
        video_codec=meta.video_codec,
        audio_codec=meta.audio_codec,
    )


def _has_audio_stream(path: Path) -> bool:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=30
        )
        payload = json.loads(completed.stdout or "{}")
        return bool(payload.get("streams"))
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return False


def detect_ffmpeg_hwaccel() -> str | None:
    """Return a usable hwaccel name if present, else None (CPU decode)."""
    try:
        completed = subprocess.run(
            ["ffmpeg", "-hide_banner", "-hwaccels"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

    available = {
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip() and "Hardware" not in line
    }
    for candidate in ("cuda", "vaapi", "qsv", "videotoolbox"):
        if candidate in available:
            # Availability in the binary does not guarantee a device; callers
            # should fall back on failure.
            return candidate
    return None


class FrameReader:
    """Sequential BGR frame reader via OpenCV (CPU decode with optional fallbacks)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._cap = cv2.VideoCapture(str(path))
        if not self._cap.isOpened():
            raise AppError(
                code="video_open_failed",
                message="Unable to open source video",
                status_code=422,
            )
        self.info = probe_stream(path)
        self.index = 0

    def __iter__(self) -> FrameReader:
        return self

    def __next__(self) -> tuple[int, float, object]:
        ok, frame = self._cap.read()
        if not ok or frame is None:
            raise StopIteration
        time_seconds = self.index / self.info.fps if self.info.fps > 0 else 0.0
        current = self.index
        self.index += 1
        return current, time_seconds, frame

    def release(self) -> None:
        self._cap.release()


class FrameWriter:
    """
    Writes processed frames to an intermediate video, then muxes original audio.

    Intermediate video is encoded with libx264 at the source fps/resolution.
    Audio is stream-copied from the source when present.
    """

    def __init__(
        self,
        *,
        output_path: Path,
        source_path: Path,
        info: VideoStreamInfo,
        temp_dir: Path,
    ) -> None:
        if not ffmpeg_available():
            raise AppError(
                code="ffmpeg_missing",
                message="ffmpeg is required for video encoding",
                status_code=503,
            )
        self.output_path = output_path
        self.source_path = source_path
        self.info = info
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._video_only = self.temp_dir / "video_only.mp4"

        # OpenCV writer for reliable frame-accurate BGR input; ffmpeg remuxes audio.
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(
            str(self._video_only),
            fourcc,
            info.fps,
            (info.width, info.height),
        )
        if not self._writer.isOpened():
            raise AppError(
                code="encoder_open_failed",
                message="Unable to open video encoder",
                status_code=500,
            )

    def write(self, frame_bgr) -> None:  # noqa: ANN001
        if frame_bgr.shape[1] != self.info.width or frame_bgr.shape[0] != self.info.height:
            raise AppError(
                code="frame_size_mismatch",
                message="Processed frame resolution does not match source",
                status_code=500,
                details={
                    "expected": [self.info.width, self.info.height],
                    "got": [int(frame_bgr.shape[1]), int(frame_bgr.shape[0])],
                },
            )
        self._writer.write(frame_bgr)

    def finalize(self) -> Path:
        self._writer.release()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.info.has_audio:
            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(self._video_only),
                "-i",
                str(self.source_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0?",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-shortest",
                "-movflags",
                "+faststart",
                str(self.output_path),
            ]
        else:
            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(self._video_only),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                "-movflags",
                "+faststart",
                str(self.output_path),
            ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=max(120, int(self.info.duration_seconds * 10) + 60),
            )
        except subprocess.CalledProcessError as exc:
            raise AppError(
                code="encode_failed",
                message="Failed to encode processed MP4",
                status_code=500,
                details={"stderr": (exc.stderr or "")[:800]},
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise AppError(
                code="encode_timeout",
                message="Timed out while encoding processed MP4",
                status_code=504,
            ) from exc

        return self.output_path

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
