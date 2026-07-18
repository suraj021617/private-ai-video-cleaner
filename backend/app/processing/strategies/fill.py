"""Solid fill strategy — replaces masked pixels with a constant color."""

from __future__ import annotations

from typing import ClassVar

import numpy as np

from app.processing.strategies.base import ProcessingPlugin, count_mask_pixels
from app.processing.types import (
    FrameContext,
    ProcessFrameResult,
    ProcessingStrategy,
    StrategyOptions,
)


class FillPlugin(ProcessingPlugin):
    name: ClassVar[ProcessingStrategy] = ProcessingStrategy.FILL

    def process_frame(
        self, ctx: FrameContext, options: StrategyOptions
    ) -> ProcessFrameResult:
        pixels = count_mask_pixels(ctx.mask)
        if pixels == 0:
            return self.empty_result(ctx)

        filled = ctx.frame_bgr.copy()
        color = np.array(options.fill_color_bgr, dtype=filled.dtype)
        filled[ctx.mask > 0] = color
        composed = self.composite(ctx.frame_bgr, filled, ctx.mask)
        return ProcessFrameResult(
            frame_bgr=composed,
            strategy=self.name,
            device=ctx.device,
            pixels_modified=pixels,
        )
