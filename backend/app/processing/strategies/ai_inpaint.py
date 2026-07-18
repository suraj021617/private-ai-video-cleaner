"""
AI inpainting strategy — real LaMa pipeline.

Processes only the padded crop around the user mask, blends with feathering,
falls back to CPU on CUDA OOM, and never modifies pixels outside the mask.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from app.core.config import get_settings
from app.core.errors import AppError
from app.processing.plugins.lama import get_model_manager, inpaint_frame_with_lama
from app.processing.strategies.base import ProcessingPlugin, count_mask_pixels
from app.processing.types import (
    ComputeDevice,
    FrameContext,
    ProcessFrameResult,
    ProcessingStrategy,
    StrategyOptions,
)


def _torch_available() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


class AIInpaintPlugin(ProcessingPlugin):
    name: ClassVar[ProcessingStrategy] = ProcessingStrategy.AI_INPAINT
    available: ClassVar[bool] = True

    def process_frame(
        self, ctx: FrameContext, options: StrategyOptions
    ) -> ProcessFrameResult:
        pixels = count_mask_pixels(ctx.mask)
        if pixels == 0:
            return self.empty_result(ctx)

        if not _torch_available():
            raise AppError(
                code="torch_missing",
                message="PyTorch is required for AI (LaMa) inpainting. Install torch and retry.",
                status_code=503,
            )

        settings = get_settings()
        model_dir = Path(options.extras.get("model_dir") or settings.lama_model_dir)
        prefer_gpu = bool(options.extras.get("prefer_gpu", settings.lama_prefer_gpu))
        padding = int(options.extras.get("padding", settings.lama_padding))
        blend_strength = float(
            options.extras.get("blend_strength", settings.lama_blend_strength)
        )
        feather = int(options.extras.get("feather_radius", settings.lama_feather_radius))

        manager = get_model_manager(model_dir, prefer_gpu=prefer_gpu)
        try:
            processed, stats = inpaint_frame_with_lama(
                ctx.frame_bgr,
                ctx.mask,
                manager,
                padding=padding,
                blend_strength=blend_strength,
                feather_radius=feather,
                prefer_gpu=prefer_gpu,
            )
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="lama_inference_failed",
                message=f"LaMa inpainting failed: {exc}",
                status_code=500,
            ) from exc

        device_name = str(stats.get("device") or "cpu")
        device = (
            ComputeDevice.CUDA if device_name.startswith("cuda") else ComputeDevice.CPU
        )
        return ProcessFrameResult(
            frame_bgr=processed,
            strategy=self.name,
            device=device,
            pixels_modified=pixels,
        )
