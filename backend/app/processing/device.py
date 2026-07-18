"""Compute device detection: CUDA → OpenCL → CPU."""

from __future__ import annotations

import logging

import cv2

from app.processing.types import ComputeDevice

logger = logging.getLogger(__name__)


def detect_compute_device(*, prefer_gpu: bool = True) -> ComputeDevice:
    """Return the best available device for OpenCV acceleration."""
    if not prefer_gpu:
        return ComputeDevice.CPU

    try:
        if hasattr(cv2, "cuda") and cv2.cuda.getCudaEnabledDeviceCount() > 0:
            logger.info("Using CUDA acceleration (%s device(s))", cv2.cuda.getCudaEnabledDeviceCount())
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
