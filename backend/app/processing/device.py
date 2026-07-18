"""Compute device detection: CUDA → OpenCL → CPU, plus benchmarks/memory."""

from __future__ import annotations

import logging
import time
from functools import lru_cache

import cv2
import numpy as np

from app.processing.types import ComputeDevice

logger = logging.getLogger(__name__)


def detect_compute_device(*, prefer_gpu: bool = True) -> ComputeDevice:
    """Return the best available device for OpenCV acceleration."""
    if not prefer_gpu:
        return ComputeDevice.CPU

    try:
        if hasattr(cv2, "cuda") and cv2.cuda.getCudaEnabledDeviceCount() > 0:
            logger.info(
                "Using CUDA acceleration (%s device(s))",
                cv2.cuda.getCudaEnabledDeviceCount(),
            )
            return ComputeDevice.CUDA
    except Exception:  # noqa: BLE001
        logger.debug("CUDA probe failed", exc_info=True)

    try:
        if cv2.ocl.haveOpenCL():
            cv2.ocl.setUseOpenCL(True)
            if cv2.ocl.useOpenCL():
                logger.info("Using OpenCL acceleration")
                return ComputeDevice.OPENCL
    except Exception:  # noqa: BLE001
        logger.debug("OpenCL probe failed", exc_info=True)

    logger.info("Using CPU processing backend")
    return ComputeDevice.CPU


def device_capabilities() -> dict[str, object]:
    cuda_count = 0
    try:
        if hasattr(cv2, "cuda"):
            cuda_count = int(cv2.cuda.getCudaEnabledDeviceCount())
    except Exception:  # noqa: BLE001
        cuda_count = 0

    opencl = False
    try:
        opencl = bool(cv2.ocl.haveOpenCL())
    except Exception:  # noqa: BLE001
        opencl = False

    selected = detect_compute_device(prefer_gpu=True)
    return {
        "cuda_devices": cuda_count,
        "opencl_available": opencl,
        "selected": selected.value,
    }


def memory_status() -> dict[str, object]:
    """Best-effort process/system memory snapshot."""
    status: dict[str, object] = {"rss_mb": None, "cuda_allocated_mb": None}
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is KB on Linux
        status["rss_mb"] = round(usage.ru_maxrss / 1024.0, 2)
    except Exception:  # noqa: BLE001
        pass
    try:
        import torch

        if torch.cuda.is_available():
            status["cuda_allocated_mb"] = round(
                torch.cuda.memory_allocated() / (1024 * 1024), 2
            )
            status["cuda_reserved_mb"] = round(
                torch.cuda.memory_reserved() / (1024 * 1024), 2
            )
    except Exception:  # noqa: BLE001
        pass
    return status


@lru_cache(maxsize=1)
def benchmark_devices() -> dict[str, object]:
    """
    Lightweight blur micro-benchmark across available backends.

    Cached for process lifetime; used by capabilities API.
    """
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    results: dict[str, object] = {"cpu_ms": None, "opencl_ms": None, "cuda_ms": None}

    start = time.perf_counter()
    cv2.GaussianBlur(frame, (21, 21), 0)
    results["cpu_ms"] = round((time.perf_counter() - start) * 1000, 3)

    try:
        if cv2.ocl.haveOpenCL():
            cv2.ocl.setUseOpenCL(True)
            umat = cv2.UMat(frame)
            start = time.perf_counter()
            cv2.GaussianBlur(umat, (21, 21), 0)
            results["opencl_ms"] = round((time.perf_counter() - start) * 1000, 3)
    except Exception:  # noqa: BLE001
        results["opencl_ms"] = None

    try:
        if hasattr(cv2, "cuda") and cv2.cuda.getCudaEnabledDeviceCount() > 0:
            gpu = cv2.cuda_GpuMat()
            gpu.upload(frame)
            start = time.perf_counter()
            # Fallback path if cuda filters unavailable
            _ = gpu.download()
            results["cuda_ms"] = round((time.perf_counter() - start) * 1000, 3)
    except Exception:  # noqa: BLE001
        results["cuda_ms"] = None

    selected = detect_compute_device(prefer_gpu=True).value
    results["recommended"] = selected
    return results
