"""
AI inpainting plugin slot.

Registered for future use. Selecting this strategy fails closed until a real
model backend is wired. Do not claim AI removal is available.
"""

from __future__ import annotations

from typing import ClassVar

from app.core.errors import AppError
from app.processing.strategies.base import ProcessingPlugin
from app.processing.types import (
    FrameContext,
    ProcessFrameResult,
    ProcessingStrategy,
    StrategyOptions,
)


class AIInpaintPlugin(ProcessingPlugin):
    name: ClassVar[ProcessingStrategy] = ProcessingStrategy.AI_INPAINT
    available: ClassVar[bool] = False

    def process_frame(
        self, ctx: FrameContext, options: StrategyOptions
    ) -> ProcessFrameResult:
        raise AppError(
            code="ai_inpaint_unavailable",
            message="AI inpainting is not implemented yet. Use blur, fill, or classic_inpaint.",
            status_code=501,
        )
