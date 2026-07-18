"""Processing plugin protocol and base helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

import numpy as np

from app.processing.types import (
    ComputeDevice,
    FrameContext,
    ProcessFrameResult,
    ProcessingStrategy,
    StrategyOptions,
)


class ProcessingPlugin(ABC):
    """
    Strategy plugin interface.

    Future AI inpainting implements the same contract:
      process_frame(ctx, options) -> ProcessFrameResult
    and must only alter pixels where ctx.mask > 0.
    """

    name: ClassVar[ProcessingStrategy]
    available: ClassVar[bool] = True

    @abstractmethod
    def process_frame(
        self,
        ctx: FrameContext,
        options: StrategyOptions,
    ) -> ProcessFrameResult:
        raise NotImplementedError

    def composite(
        self,
        original: np.ndarray,
        modified_region: np.ndarray,
        mask: np.ndarray,
    ) -> np.ndarray:
        """Copy modified pixels only inside the mask; leave outside untouched."""
        out = original.copy()
        mask_bool = mask > 0
        out[mask_bool] = modified_region[mask_bool]
        return out

    def empty_result(
        self, ctx: FrameContext
    ) -> ProcessFrameResult:
        return ProcessFrameResult(
            frame_bgr=ctx.frame_bgr,
            strategy=self.name,
            device=ctx.device,
            pixels_modified=0,
        )


def count_mask_pixels(mask: np.ndarray) -> int:
    return int(np.count_nonzero(mask))
