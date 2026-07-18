"""FFmpeg-backed decode/encode helpers preserving fps, resolution, and audio."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

import cv2

from app.core.errors import AppError
from app.processing.types import ExportOptions, VideoStreamInfo
from app.services.probe import probe_video

logger = logging.getLogger(__name__)

_QUALITY_CRF = {
    "fast": {"h264": 28, "hevc": 32},
    "balanced": {"h264": 23, "hevc": 28},
    "best": {"h264": 18, "hevc": 22},
}
_QUALITY_PRESET = {
    "fast": "veryfast",
    "balanced": "medium",
    "best": "slow",
}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def probe_stream(path: Path) -> VideoStreamInfo:
    meta = probe_video(path)
    color = _probe_color_and_hdr(path)
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
        pixel_format=color.get("pix_fmt"),
        color_space=color.get("color_space"),
        color_transfer=color.get("color_transfer"),
        color_primaries=color.get("color_primaries"),
        rotation=color.get("rotation"),
        bit_rate=color.get("bit_rate"),
        hdr=bool(color.get("hdr")),
    )


def _probe_color_and_hdr(path: Path) -> dict:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=pix_fmt,color_space,color_transfer,color_primaries,bit_rate:"
        "stream_side_data=rotation:"
        "stream_tags=rotate",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=30
        )
        payload = json.loads(completed.stdout or "{}")
        streams = payload.get("streams") or []
        if not streams:
            return {}
        stream = streams[0]
        transfer = (stream.get("color_transfer") or "").lower()
        primaries = (stream.get("color_primaries") or "").lower()
        hdr = any(
            token in transfer or token in primaries
            for token in ("smpte2084", "arib-std-b67", "bt2020")
        )
        rotation = None
        tags = stream.get("tags") or {}
        if tags.get("rotate"):
            try:
                rotation = int(tags["rotate"])
            except (TypeError, ValueError):
                rotation = None
        bit_rate = None
        if stream.get("bit_rate"):
            try:
                bit_rate = int(stream["bit_rate"])
            except (TypeError, ValueError):
                bit_rate = None
        return {
            "pix_fmt": stream.get("pix_fmt"),
            "color_space": stream.get("color_space"),
            "color_transfer": stream.get("color_transfer"),
            "color_primaries": stream.get("color_primaries"),
            "rotation": rotation,
            "bit_rate": bit_rate,
            "hdr": hdr,
        }
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        return {}


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

    Preserves source fps/resolution by default. Supports MP4/MOV/MKV, H264/HEVC,
    quality presets, optional 4K target, and best-effort HDR/color metadata copy.
    """

    def __init__(
        self,
        *,
        output_path: Path,
        source_path: Path,
        info: VideoStreamInfo,
        temp_dir: Path,
        container: str = "mp4",
        export: ExportOptions | None = None,
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
        self.export = export or ExportOptions(container=container)
        allowed = {"mp4", "mov", "mkv"}
        self.container = (
            self.export.container
            if self.export.container in allowed
            else (container if container in allowed else "mp4")
        )
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._video_only = self.temp_dir / "video_only.mp4"

        out_w = self.export.target_width or info.width
        out_h = self.export.target_height or info.height
        # Keep even dimensions for yuv420p
        self.out_width = out_w - (out_w % 2)
        self.out_height = out_h - (out_h % 2)

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

    def _video_encoder_args(self) -> list[str]:
        codec = (self.export.codec or "h264").lower()
        quality = (self.export.quality or "balanced").lower()
        if quality not in _QUALITY_CRF:
            quality = "balanced"
        if codec == "hevc":
            encoder = "libx265"
            crf = str(_QUALITY_CRF[quality]["hevc"])
            x265 = ["-x265-params", f"log-level=error"]
        else:
            encoder = "libx264"
            crf = str(_QUALITY_CRF[quality]["h264"])
            x265 = []
        preset = _QUALITY_PRESET[quality]
        args = [
            "-c:v",
            encoder,
            "-preset",
            preset,
            "-crf",
            crf,
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(self.info.fps),
            *x265,
        ]
        # Best-effort bitrate hint when source bitrate known
        if self.info.bit_rate and quality == "best":
            args.extend(["-b:v", str(self.info.bit_rate)])
        return args

    def _color_metadata_args(self) -> list[str]:
        args: list[str] = []
        if not self.export.preserve_hdr:
            return args
        if self.info.color_space:
            args.extend(["-colorspace", str(self.info.color_space)])
        if self.info.color_transfer:
            args.extend(["-color_trc", str(self.info.color_transfer)])
        if self.info.color_primaries:
            args.extend(["-color_primaries", str(self.info.color_primaries)])
        return args

    def finalize(self) -> Path:
        self._writer.release()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        scale_filter = None
        if (
            self.out_width != self.info.width
            or self.out_height != self.info.height
        ):
            scale_filter = f"scale={self.out_width}:{self.out_height}:flags=lanczos"

        movflags = ["-movflags", "+faststart"] if self.container == "mp4" else []
        v_args = self._video_encoder_args()
        color_args = self._color_metadata_args()
        vf = ["-vf", scale_filter] if scale_filter else []
        # ffmpeg muxer name for .mkv is "matroska"
        muxer = "matroska" if self.container == "mkv" else self.container

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
                *vf,
                *v_args,
                *color_args,
                "-c:a",
                "copy",
                "-shortest",
                "-f",
                muxer,
                *movflags,
                "-map_metadata",
                "1",
                str(self.output_path),
            ]
        else:
            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(self._video_only),
                *vf,
                *v_args,
                *color_args,
                "-an",
                "-f",
                muxer,
                *movflags,
                str(self.output_path),
            ]

        timeout = max(120, int(self.info.duration_seconds * 10) + 60)
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.CalledProcessError as exc:
            # HEVC may be missing — retry once with H264 using same temp video.
            if (self.export.codec or "").lower() == "hevc":
                logger.warning("HEVC encode failed; retrying with H264")
                self.export.codec = "h264"
                v_args = self._video_encoder_args()
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
                        *vf,
                        *v_args,
                        *color_args,
                        "-c:a",
                        "copy",
                        "-shortest",
                        "-f",
                        muxer,
                        *movflags,
                        "-map_metadata",
                        "1",
                        str(self.output_path),
                    ]
                else:
                    command = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(self._video_only),
                        *vf,
                        *v_args,
                        *color_args,
                        "-an",
                        "-f",
                        muxer,
                        *movflags,
                        str(self.output_path),
                    ]
                try:
                    subprocess.run(
                        command,
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                except subprocess.CalledProcessError as retry_exc:
                    raise AppError(
                        code="encode_failed",
                        message="Failed to encode processed video",
                        status_code=500,
                        details={"stderr": (retry_exc.stderr or "")[:800]},
                    ) from retry_exc
            else:
                raise AppError(
                    code="encode_failed",
                    message="Failed to encode processed video",
                    status_code=500,
                    details={"stderr": (exc.stderr or "")[:800]},
                ) from exc
        except subprocess.TimeoutExpired as exc:
            raise AppError(
                code="encode_timeout",
                message="Timed out while encoding processed video",
                status_code=504,
            ) from exc

        return self.output_path

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
