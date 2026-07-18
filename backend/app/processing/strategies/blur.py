"""Blur strategy — CPU / OpenCL UMat / CUDA when available."""

from __future__ import annotations

from typing import ClassVar

import cv2
import numpy as np

from app.processing.strategies.base import ProcessingPlugin, count_mask_pixels
from app.processing.types import (
    ComputeDevice,
    FrameContext,
    ProcessFrameResult,
    ProcessingStrategy,
    StrategyOptions,
)


class BlurPlugin(ProcessingPlugin):
    name: ClassVar[ProcessingStrategy] = ProcessingStrategy.BLUR

    def process_frame(
        self, ctx: FrameContext, options: StrategyOptions
    ) -> ProcessFrameResult:
        if count_mask_pixels(ctx.mask) == 0:
            return self.empty_result(ctx)

        ksize = options.normalized_ksize()
        if ctx.device == ComputeDevice.CUDA and hasattr(cv2, "cuda"):
            blurred = self._blur_cuda(ctx.frame_bgr, ksize)
            device = ComputeDevice.CUDA
        elif ctx.device == ComputeDevice.OPENCL:
            blurred = self._blur_opencl(ctx.frame_bgr, ksize)
            device = ComputeDevice.OPENCL
        else:
            blurred = cv2.GaussianBlur(ctx.frame_bgr, (ksize, ksize), 0)
            device = ComputeDevice.CPU

        composed = self.composite(ctx.frame_bgr, blurred, ctx.mask)
        return ProcessFrameResult(
            frame_bgr=composed,
            strategy=self.name,
            device=device,
            pixels_modified=count_mask_pixels(ctx.mask),
        )

    def _blur_cuda(self, frame: np.ndarray, ksize: int) -> np.ndarray:
        try:
            gpu = cv2.cuda_GpuMat()
            gpu.upload(frame)
            filtered = cv2.cuda.createGaussianFilter(
                gpu.type(), -1, (ksize, ksize), 0
            )
            out = filtered.apply(gpu)
            return out.download()
        except Exception:  # noqa: BLE001
            return cv2.GaussianBlur(frame, (ksize, ksize), 0)

    def _blur_opencl(self, frame: np.ndarray, ksize: int) -> np.ndarray:
        try:
            umat = cv2.UMat(frame)
            blurred = cv2.GaussianBlur(umat, (ksize, ksize), 0)
            return blurred.get()
        except Exception:  # noqa: BLE001
            return cv2.GaussianBlur(frame, (ksize, ksize), 0)
