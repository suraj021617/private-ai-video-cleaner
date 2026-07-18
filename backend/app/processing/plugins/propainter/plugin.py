"""ProPainter plugin slot — falls back when package/model unavailable."""

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


def propainter_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("propainter") is not None
    except Exception:  # noqa: BLE001
        return False


class ProPainterPlugin(ProcessingPlugin):
    name: ClassVar[ProcessingStrategy] = ProcessingStrategy.PROPAINTER
    available: ClassVar[bool] = False  # enabled dynamically via registry check

    def process_frame(
        self, ctx: FrameContext, options: StrategyOptions
    ) -> ProcessFrameResult:
        if not propainter_available():
            raise AppError(
                code="propainter_unavailable",
                message=(
                    "ProPainter is not installed. Falling back is handled by the "
                    "job runner — install propainter to enable temporal AI inpainting."
                ),
                status_code=501,
            )
        raise AppError(
            code="propainter_not_wired",
            message="ProPainter package found but runtime adapter is not configured in this build.",
            status_code=501,
        )
