"""Production diagnostics: system, models, benchmarks, video/export tests, reports."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app import __version__
from app.core.config import Settings
from app.core.errors import AppError
from app.processing.device import benchmark_devices, device_capabilities, memory_status
from app.processing.pipeline import VideoProcessingPipeline, cleanup_work_dir
from app.processing.plugins.lama import get_model_manager
from app.processing.plugins.propainter import propainter_available
from app.processing.plugins.sttn import sttn_available
from app.processing.strategies import list_strategies
from app.processing.types import ExportOptions, ProcessingStrategy, StrategyOptions

logger = logging.getLogger(__name__)

CheckStatus = str  # ok | warning | error | missing


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check(
    name: str,
    *,
    status: CheckStatus,
    detail: str,
    value: Any = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "ok": status == "ok",
        "detail": detail,
        "value": value,
    }


def _run(cmd: list[str], timeout: float = 15.0) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return completed.returncode, completed.stdout or "", completed.stderr or ""
    except FileNotFoundError:
        return 127, "", "not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def collect_system_diagnostics(settings: Settings) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # FFmpeg
    code, out, err = _run(["ffmpeg", "-version"])
    if code == 0:
        line = (out.splitlines() or ["ffmpeg"])[0]
        checks.append(_check("FFmpeg", status="ok", detail=line, value=line))
    else:
        checks.append(
            _check(
                "FFmpeg",
                status="missing",
                detail="FFmpeg not found on PATH. Install FFmpeg to encode/export.",
            )
        )

    # FFprobe
    code, out, err = _run(["ffprobe", "-version"])
    if code == 0:
        line = (out.splitlines() or ["ffprobe"])[0]
        checks.append(_check("FFprobe", status="ok", detail=line, value=line))
    else:
        checks.append(
            _check(
                "FFprobe",
                status="missing",
                detail="FFprobe not found. Metadata probing will fail.",
            )
        )

    # OpenCV
    try:
        checks.append(
            _check(
                "OpenCV",
                status="ok",
                detail=f"OpenCV {cv2.__version__}",
                value=cv2.__version__,
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            _check("OpenCV", status="error", detail=f"OpenCV unavailable: {exc}")
        )

    # Python
    checks.append(
        _check(
            "Python",
            status="ok",
            detail=sys.version.split()[0],
            value=platform.python_version(),
        )
    )

    # CUDA / GPU
    cuda_ok = False
    cuda_version = None
    gpu_name = None
    gpu_mem = None
    try:
        import torch

        cuda_ok = bool(torch.cuda.is_available())
        if cuda_ok:
            cuda_version = getattr(torch.version, "cuda", None)
            gpu_name = torch.cuda.get_device_name(0)
            try:
                props = torch.cuda.get_device_properties(0)
                gpu_mem = round(props.total_memory / (1024**3), 2)
            except Exception:  # noqa: BLE001
                gpu_mem = None
            checks.append(
                _check(
                    "CUDA",
                    status="ok",
                    detail=f"Available (CUDA {cuda_version})",
                    value=cuda_version,
                )
            )
            checks.append(
                _check(
                    "GPU model",
                    status="ok",
                    detail=str(gpu_name),
                    value=gpu_name,
                )
            )
            checks.append(
                _check(
                    "GPU memory",
                    status="ok" if gpu_mem else "warning",
                    detail=f"{gpu_mem} GB" if gpu_mem else "Unknown",
                    value=gpu_mem,
                )
            )
        else:
            checks.append(
                _check(
                    "CUDA",
                    status="warning",
                    detail="CUDA not available — processing will use CPU (slower).",
                )
            )
            checks.append(
                _check(
                    "GPU model",
                    status="warning",
                    detail="No CUDA GPU detected",
                )
            )
            checks.append(
                _check(
                    "GPU memory",
                    status="warning",
                    detail="N/A without CUDA",
                )
            )
    except Exception:  # noqa: BLE001
        checks.append(
            _check(
                "CUDA",
                status="warning",
                detail="PyTorch not installed — AI (LaMa) unavailable; classic strategies work.",
            )
        )
        checks.append(
            _check("GPU model", status="warning", detail="Unknown (torch missing)")
        )
        checks.append(
            _check("GPU memory", status="warning", detail="Unknown (torch missing)")
        )

    # OpenCL via OpenCV
    opencl = False
    try:
        opencl = bool(cv2.ocl.haveOpenCL())
    except Exception:  # noqa: BLE001
        opencl = False
    checks.append(
        _check(
            "OpenCL",
            status="ok" if opencl else "warning",
            detail="Available" if opencl else "Not available — OpenCV will use CPU",
            value=opencl,
        )
    )

    # CPU
    cpu = platform.processor() or platform.machine()
    checks.append(
        _check(
            "CPU",
            status="ok",
            detail=f"{platform.machine()} · {cpu or 'unknown'} · cores≈{os.cpu_count() or '?'}",
            value={"machine": platform.machine(), "processor": cpu, "cores": os.cpu_count()},
        )
    )

    # RAM
    ram_detail = "Unknown"
    ram_gb = None
    try:
        if hasattr(os, "sysconf"):
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            if pages and page_size:
                ram_gb = round((pages * page_size) / (1024**3), 2)
                ram_detail = f"{ram_gb} GB total"
    except Exception:  # noqa: BLE001
        pass
    mem = memory_status()
    if mem.get("rss_mb") is not None:
        ram_detail += f" · process RSS {mem['rss_mb']} MB"
    checks.append(
        _check(
            "RAM",
            status="ok" if ram_gb else "warning",
            detail=ram_detail,
            value={"total_gb": ram_gb, **mem},
        )
    )

    # Disk
    try:
        usage = shutil.disk_usage(str(settings.storage_root))
        free_gb = round(usage.free / (1024**3), 2)
        total_gb = round(usage.total / (1024**3), 2)
        status: CheckStatus = "ok"
        if free_gb < 1:
            status = "error"
        elif free_gb < 5:
            status = "warning"
        checks.append(
            _check(
                "Disk space",
                status=status,
                detail=f"{free_gb} GB free of {total_gb} GB (storage root)",
                value={"free_gb": free_gb, "total_gb": total_gb},
            )
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            _check("Disk space", status="error", detail=f"Cannot inspect disk: {exc}")
        )

    # OS
    checks.append(
        _check(
            "Operating system",
            status="ok",
            detail=f"{platform.system()} {platform.release()} ({platform.platform()})",
            value=platform.platform(),
        )
    )

    # App version
    checks.append(
        _check(
            "Application version",
            status="ok",
            detail=__version__,
            value=__version__,
        )
    )

    ok_count = sum(1 for c in checks if c["status"] == "ok")
    warn_count = sum(1 for c in checks if c["status"] == "warning")
    err_count = sum(1 for c in checks if c["status"] in {"error", "missing"})
    overall = "healthy"
    if err_count:
        overall = "unhealthy"
    elif warn_count:
        overall = "degraded"

    return {
        "generated_at": _utcnow(),
        "overall": overall,
        "counts": {"ok": ok_count, "warning": warn_count, "error": err_count},
        "checks": checks,
        "capabilities": device_capabilities(),
    }


def _file_sha256(path: Path, max_bytes: int = 8 * 1024 * 1024) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            remaining = max_bytes
            while remaining > 0:
                chunk = fh.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                h.update(chunk)
                remaining -= len(chunk)
        return h.hexdigest()
    except OSError:
        return None


def collect_model_diagnostics(settings: Settings) -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    lama_dir = Path(settings.lama_model_dir)
    checkpoint = lama_dir / "big-lama.pt"

    # Classic always-available strategies
    for name, label in (
        ("classic_inpaint", "Classic Inpaint"),
        ("blur", "Blur"),
        ("fill", "Fill"),
    ):
        models.append(
            {
                "id": name,
                "label": label,
                "exists": True,
                "readable": True,
                "compatible": True,
                "corrupted": False,
                "checksum": None,
                "path": None,
                "status": "ok",
                "detail": "Built-in OpenCV strategy — always available",
            }
        )

    # LaMa
    lama_status = "missing"
    lama_detail = "Checkpoint not found"
    corrupted = False
    checksum = None
    readable = False
    compatible = False
    exists = checkpoint.is_file()
    if exists:
        readable = os.access(checkpoint, os.R_OK)
        size = checkpoint.stat().st_size
        checksum = _file_sha256(checkpoint)
        if size < 1_000_000:
            corrupted = True
            lama_status = "error"
            lama_detail = f"Checkpoint suspiciously small ({size} bytes)"
        elif not readable:
            lama_status = "error"
            lama_detail = "Checkpoint exists but is not readable"
        else:
            try:
                import torch  # noqa: F401

                compatible = True
                lama_status = "ok"
                lama_detail = f"Found ({round(size / (1024**2), 1)} MB)"
            except Exception:  # noqa: BLE001
                compatible = False
                lama_status = "warning"
                lama_detail = "Checkpoint present but PyTorch missing"
    models.append(
        {
            "id": "ai_inpaint",
            "label": "LaMa",
            "exists": exists,
            "readable": readable,
            "compatible": compatible,
            "corrupted": corrupted,
            "checksum": checksum,
            "path": str(checkpoint) if exists else str(checkpoint),
            "status": lama_status if exists else "missing",
            "detail": lama_detail if exists else f"Expected at {checkpoint}",
        }
    )

    # ProPainter / STTN plugin slots
    for mid, label, available, hint in (
        (
            "propainter",
            "ProPainter",
            propainter_available(),
            "Optional package `propainter` — falls back to LaMa/classic",
        ),
        (
            "sttn",
            "STTN",
            sttn_available(),
            "Optional package `sttn` — falls back to LaMa/classic",
        ),
    ):
        models.append(
            {
                "id": mid,
                "label": label,
                "exists": available,
                "readable": available,
                "compatible": available,
                "corrupted": False,
                "checksum": None,
                "path": None,
                "status": "ok" if available else "warning",
                "detail": "Installed" if available else hint,
            }
        )

    strategy_info = list_strategies()
    return {
        "generated_at": _utcnow(),
        "models": models,
        "strategies": strategy_info,
        "lama_manager": get_model_manager(
            settings.lama_model_dir, prefer_gpu=settings.lama_prefer_gpu
        ).status,
    }


def refresh_models(settings: Settings) -> dict[str, Any]:
    """Ensure LaMa checkpoint is present (download if needed) and re-check models."""
    manager = get_model_manager(
        settings.lama_model_dir, prefer_gpu=settings.lama_prefer_gpu
    )
    try:
        manager.ensure_model(prefer_gpu=settings.lama_prefer_gpu)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Model refresh failed: %s", exc)
        return {
            "refreshed": False,
            "error": str(exc),
            "models": collect_model_diagnostics(settings),
        }
    return {
        "refreshed": True,
        "error": None,
        "models": collect_model_diagnostics(settings),
    }


def run_gpu_benchmark() -> dict[str, Any]:
    started = time.perf_counter()
    micro = benchmark_devices()
    mem_before = memory_status()

    # Synthetic inference-ish workload (blur loop)
    frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    mask = np.zeros((720, 1280), dtype=np.uint8)
    mask[200:500, 400:900] = 255
    frames = 24
    t0 = time.perf_counter()
    for _ in range(frames):
        blurred = cv2.GaussianBlur(frame, (31, 31), 0)
        frame = np.where(mask[..., None] > 0, blurred, frame)
    elapsed = max(time.perf_counter() - t0, 1e-6)
    fps = frames / elapsed
    mem_after = memory_status()

    cpu_util = None
    try:
        load1, _, _ = os.getloadavg()
        cores = os.cpu_count() or 1
        cpu_util = round(min(100.0, (load1 / cores) * 100), 1)
    except Exception:  # noqa: BLE001
        cpu_util = None

    return {
        "generated_at": _utcnow(),
        "device_microbench_ms": micro,
        "inference": {
            "frames": frames,
            "elapsed_seconds": round(elapsed, 4),
            "frames_per_second": round(fps, 2),
            "avg_ms_per_frame": round((elapsed / frames) * 1000, 2),
            "workload": "720p Gaussian blur masked composite",
        },
        "memory": {"before": mem_before, "after": mem_after},
        "cpu_utilization_estimate": cpu_util,
        "gpu_utilization": None,  # requires NVML; left null when unavailable
        "total_seconds": round(time.perf_counter() - started, 4),
        "chart": {
            "labels": ["CPU blur ms", "OpenCL ms", "CUDA upload ms", "Proc FPS"],
            "values": [
                micro.get("cpu_ms") or 0,
                micro.get("opencl_ms") or 0,
                micro.get("cuda_ms") or 0,
                round(fps, 2),
            ],
        },
    }


def _make_sample_video(path: Path, *, seconds: float = 0.4) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=blue:s=320x240:d={seconds}",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={seconds}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(path),
    ]
    code, _, err = _run(cmd, timeout=60)
    if code != 0 or not path.is_file():
        raise AppError(
            code="sample_video_failed",
            message="Could not generate sample video for diagnostics",
            status_code=500,
            details={"stderr": err[:400]},
        )
    return path


_MASK_PAYLOAD = {
    "version": 1,
    "video_width": 320,
    "video_height": 240,
    "fps": 25,
    "items": [
        {
            "id": "diag",
            "type": "rect",
            "x": 0.2,
            "y": 0.2,
            "w": 0.4,
            "h": 0.4,
            "start_time": 0,
            "end_time": 10,
        }
    ],
}


def run_video_strategy_tests(settings: Settings) -> dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="pavc-diag-video-"))
    sample = tmp / "sample.mp4"
    results: list[dict[str, Any]] = []
    try:
        _make_sample_video(sample)
        strategies = [
            ProcessingStrategy.BLUR,
            ProcessingStrategy.FILL,
            ProcessingStrategy.CLASSIC_INPAINT,
            ProcessingStrategy.AI_INPAINT,
        ]
        for strategy in strategies:
            out = tmp / f"out_{strategy.value}.mp4"
            work = tmp / f"work_{strategy.value}"
            mem0 = memory_status()
            t0 = time.perf_counter()
            success = False
            error = None
            used = strategy.value
            try:
                result = VideoProcessingPipeline(
                    prefer_gpu=bool(settings.lama_prefer_gpu),
                    strategy_options=StrategyOptions(
                        extras={
                            "model_dir": str(settings.lama_model_dir),
                            "prefer_gpu": bool(settings.lama_prefer_gpu),
                        }
                    ),
                    export_format="mp4",
                ).run(
                    source_path=sample,
                    output_path=out,
                    work_dir=work,
                    strategy=strategy,
                    mask_payload=_MASK_PAYLOAD,
                )
                success = out.is_file() and out.stat().st_size > 0
                used = str(result.get("strategy") or strategy.value)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                success = False
            elapsed = time.perf_counter() - t0
            mem1 = memory_status()
            results.append(
                {
                    "strategy": strategy.value,
                    "strategy_used": used,
                    "success": success,
                    "export_ok": success,
                    "elapsed_seconds": round(elapsed, 3),
                    "memory": {"before": mem0, "after": mem1},
                    "error": error,
                }
            )
            cleanup_work_dir(work)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for r in results if r["success"])
    return {
        "generated_at": _utcnow(),
        "results": results,
        "passed": passed,
        "total": len(results),
        "overall": "ok" if passed == len(results) else ("warning" if passed else "error"),
    }


def run_export_tests(settings: Settings) -> dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="pavc-diag-export-"))
    sample = tmp / "sample.mp4"
    cases = [
        ("mp4", "h264"),
        ("mov", "h264"),
        ("mkv", "h264"),
        ("mp4", "hevc"),
    ]
    results: list[dict[str, Any]] = []
    try:
        _make_sample_video(sample)
        for container, codec in cases:
            out = tmp / f"out_{container}_{codec}.{container}"
            work = tmp / f"work_{container}_{codec}"
            t0 = time.perf_counter()
            error = None
            meta: dict[str, Any] = {}
            try:
                result = VideoProcessingPipeline(
                    prefer_gpu=False,
                    export_format=container,
                    export_options=ExportOptions(
                        container=container, codec=codec, quality="fast"
                    ),
                ).run(
                    source_path=sample,
                    output_path=out,
                    work_dir=work,
                    strategy=ProcessingStrategy.FILL,
                    mask_payload=_MASK_PAYLOAD,
                )
                # Probe output
                code, stdout, _ = _run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate",
                        "-of",
                        "json",
                        str(out),
                    ],
                    timeout=30,
                )
                streams = []
                if code == 0:
                    streams = json.loads(stdout or "{}").get("streams") or []
                has_audio = any(s.get("codec_type") == "a" for s in streams)
                video = next((s for s in streams if s.get("codec_type") == "v"), {})
                width = video.get("width")
                height = video.get("height")
                fps_ok = bool(video.get("r_frame_rate"))
                meta = {
                    "has_audio": has_audio,
                    "width": width,
                    "height": height,
                    "fps_present": fps_ok,
                    "video_codec": video.get("codec_name"),
                    "pipeline": {
                        "fps": result.get("fps"),
                        "width": result.get("width"),
                        "height": result.get("height"),
                        "has_audio": result.get("has_audio"),
                    },
                }
                success = (
                    out.is_file()
                    and width == 320
                    and height == 240
                    and has_audio
                    and fps_ok
                )
            except Exception as exc:  # noqa: BLE001
                success = False
                error = str(exc)
            results.append(
                {
                    "container": container,
                    "codec": codec,
                    "success": success,
                    "elapsed_seconds": round(time.perf_counter() - t0, 3),
                    "checks": {
                        "file_exists": out.is_file() if out else False,
                        "audio_preserved": meta.get("has_audio"),
                        "resolution_preserved": meta.get("width") == 320
                        and meta.get("height") == 240,
                        "fps_preserved": meta.get("fps_present"),
                        "metadata_probed": bool(meta),
                    },
                    "meta": meta,
                    "error": error,
                }
            )
            cleanup_work_dir(work)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for r in results if r["success"])
    return {
        "generated_at": _utcnow(),
        "results": results,
        "passed": passed,
        "total": len(results),
        "overall": "ok" if passed == len(results) else ("warning" if passed else "error"),
    }


ERROR_HINTS: list[tuple[str, str, str]] = [
    (
        "ffmpeg",
        "FFmpeg is missing or failed during encode/decode.",
        "Install FFmpeg/ffprobe and ensure both are on PATH, then retry.",
    ),
    (
        "torch",
        "PyTorch is required for LaMa AI inpainting.",
        "Install full requirements (`pip install -r requirements.txt`) or use Classic/Blur/Fill / lite mode.",
    ),
    (
        "cuda",
        "GPU/CUDA issue or out-of-memory during AI processing.",
        "Close other GPU apps, lower resolution, or disable GPU in Settings (CPU fallback).",
    ),
    (
        "out of memory",
        "Ran out of memory while processing.",
        "Use a shorter clip, Fast quality, or lite/classic strategies; free RAM/GPU memory.",
    ),
    (
        "mask",
        "Selection mask missing or empty.",
        "Draw a rectangle/brush region (or run Auto-detect) before processing.",
    ),
    (
        "strategy_unavailable",
        "Requested AI strategy is not installed.",
        "The job should auto-fall back; pick LaMa or Classic explicitly if needed.",
    ),
    (
        "encode",
        "Export/encode failed.",
        "Try MP4 + H.264 + Fast. Install a full FFmpeg build if HEVC/MKV fails.",
    ),
]


def explain_error(message: str | None, code: str | None = None) -> dict[str, Any]:
    text = f"{code or ''} {message or ''}".lower()
    for needle, reason, fix in ERROR_HINTS:
        if needle in text:
            return {
                "reason": reason,
                "suggested_fix": fix,
                "matched": needle,
                "original": message,
                "code": code,
            }
    return {
        "reason": message or "Unknown processing failure",
        "suggested_fix": "Open Diagnostics → Logs, check FFmpeg/models, retry with Classic strategy.",
        "matched": None,
        "original": message,
        "code": code,
    }


def build_health_report(settings: Settings) -> dict[str, Any]:
    system = collect_system_diagnostics(settings)
    models = collect_model_diagnostics(settings)
    bench = run_gpu_benchmark()
    # Keep report generation relatively fast: skip full video/export unless requested
    warnings = [
        c for c in system["checks"] if c["status"] == "warning"
    ] + [m for m in models["models"] if m["status"] == "warning"]
    errors = [
        c for c in system["checks"] if c["status"] in {"error", "missing"}
    ] + [m for m in models["models"] if m["status"] in {"error", "missing"}]

    report = {
        "generated_at": _utcnow(),
        "app_version": __version__,
        "overall": system["overall"],
        "system": system,
        "gpu": {
            "capabilities": system.get("capabilities"),
            "benchmark": bench,
        },
        "drivers": {
            "cuda": next(
                (c for c in system["checks"] if c["name"] == "CUDA"), None
            ),
            "opencl": next(
                (c for c in system["checks"] if c["name"] == "OpenCL"), None
            ),
        },
        "models": models,
        "performance": bench,
        "export": {
            "note": "Run POST /diagnostics/export-test for full container/codec verification",
        },
        "errors": errors,
        "warnings": warnings,
    }
    return report


def report_as_text(report: dict[str, Any]) -> str:
    lines = [
        "Private AI Video Cleaner — Health Report",
        f"Generated: {report.get('generated_at')}",
        f"Version: {report.get('app_version')}",
        f"Overall: {report.get('overall')}",
        "",
        "== System ==",
    ]
    for c in report.get("system", {}).get("checks", []):
        mark = "OK" if c.get("status") == "ok" else c.get("status", "?").upper()
        lines.append(f"[{mark}] {c.get('name')}: {c.get('detail')}")
    lines.append("")
    lines.append("== Models ==")
    for m in report.get("models", {}).get("models", []):
        mark = "OK" if m.get("status") == "ok" else m.get("status", "?").upper()
        lines.append(f"[{mark}] {m.get('label')}: {m.get('detail')}")
    lines.append("")
    lines.append("== Performance ==")
    inf = report.get("performance", {}).get("inference", {})
    lines.append(
        f"Frames/sec: {inf.get('frames_per_second')} · "
        f"Avg ms/frame: {inf.get('avg_ms_per_frame')}"
    )
    if report.get("errors"):
        lines.append("")
        lines.append("== Errors ==")
        for e in report["errors"]:
            lines.append(f"- {e.get('name') or e.get('label')}: {e.get('detail')}")
    if report.get("warnings"):
        lines.append("")
        lines.append("== Warnings ==")
        for w in report["warnings"]:
            lines.append(f"- {w.get('name') or w.get('label')}: {w.get('detail')}")
    lines.append("")
    return "\n".join(lines)
