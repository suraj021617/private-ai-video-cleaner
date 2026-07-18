"""Strategy registry for the processing pipeline."""

from __future__ import annotations

from app.core.errors import AppError
from app.processing.strategies.ai_inpaint import AIInpaintPlugin
from app.processing.strategies.base import ProcessingPlugin
from app.processing.strategies.blur import BlurPlugin
from app.processing.strategies.classic_inpaint import ClassicInpaintPlugin
from app.processing.strategies.fill import FillPlugin
from app.processing.types import ProcessingStrategy

_REGISTRY: dict[ProcessingStrategy, ProcessingPlugin] = {
    ProcessingStrategy.BLUR: BlurPlugin(),
    ProcessingStrategy.FILL: FillPlugin(),
    ProcessingStrategy.CLASSIC_INPAINT: ClassicInpaintPlugin(),
    ProcessingStrategy.AI_INPAINT: AIInpaintPlugin(),
}


def get_plugin(strategy: ProcessingStrategy | str) -> ProcessingPlugin:
    try:
        key = (
            strategy
            if isinstance(strategy, ProcessingStrategy)
            else ProcessingStrategy(strategy)
        )
    except ValueError as exc:
        raise AppError(
            code="unsupported_strategy",
            message=f"Unknown processing strategy: {strategy}",
            status_code=400,
            details={"allowed": [s.value for s in ProcessingStrategy]},
        ) from exc

    plugin = _REGISTRY.get(key)
    if plugin is None:
        raise AppError(
            code="unsupported_strategy",
            message=f"No plugin registered for {key}",
            status_code=400,
        )
    return plugin


def list_strategies() -> list[dict[str, object]]:
    return [
        {
            "name": strategy.value,
            "available": plugin.available,
        }
        for strategy, plugin in _REGISTRY.items()
    ]
