"""Classic OpenCV inpainting (Telea / Navier-Stokes). Not AI."""

from __future__ import annotations

from typing import ClassVar

import cv2

from app.processing.strategies.base import ProcessingPlugin, count_mask_pixels
from app.processing.types import (
    ComputeDevice,
    FrameContext,
    ProcessFrameResult,
    ProcessingStrategy,
    StrategyOptions,
)


class ClassicInpaintPlugin(ProcessingPlugin):
    name: ClassVar[ProcessingStrategy] = ProcessingStrategy.CLASSIC_INPAINT

    def process_frame(
        self, ctx: FrameContext, options: StrategyOptions
    ) -> ProcessFrameResult:
        pixels = count_mask_pixels(ctx.mask)
        if pixels == 0:
            return self.empty_result(ctx)

        method = (
            cv2.INPAINT_TELEA
            if options.inpaint_method.lower() != "ns"
            else cv2.INPAINT_NS
        )
        radius = max(1, int(options.inpaint_radius))

        # OpenCV inpaint runs on CPU; device selection still applies to other plugins.
        inpainted = cv2.inpaint(ctx.frame_bgr, ctx.mask, radius, method)
        composed = self.composite(ctx.frame_bgr, inpainted, ctx.mask)
        return ProcessFrameResult(
            frame_bgr=composed,
            strategy=self.name,
            device=ComputeDevice.CPU,
            pixels_modified=pixels,
        )
