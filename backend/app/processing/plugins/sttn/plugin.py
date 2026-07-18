"""STTN plugin slot — falls back when package/model unavailable."""

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


def sttn_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("sttn") is not None
    except Exception:  # noqa: BLE001
        return False


class STTNPlugin(ProcessingPlugin):
    name: ClassVar[ProcessingStrategy] = ProcessingStrategy.STTN
    available: ClassVar[bool] = False

    def process_frame(
        self, ctx: FrameContext, options: StrategyOptions
    ) -> ProcessFrameResult:
        if not sttn_available():
            raise AppError(
                code="sttn_unavailable",
                message=(
                    "STTN is not installed. The job runner will fall back to LaMa "
                    "or classic_inpaint automatically."
                ),
                status_code=501,
            )
        raise AppError(
            code="sttn_not_wired",
            message="STTN package found but runtime adapter is not configured in this build.",
            status_code=501,
        )
