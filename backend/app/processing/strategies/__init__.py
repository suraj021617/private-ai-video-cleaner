"""Strategy registry for the processing pipeline."""

from __future__ import annotations

from app.core.errors import AppError
from app.processing.plugins.propainter import ProPainterPlugin, propainter_available
from app.processing.plugins.sttn import STTNPlugin, sttn_available
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
    ProcessingStrategy.PROPAINTER: ProPainterPlugin(),
    ProcessingStrategy.STTN: STTNPlugin(),
}

# Prefer temporal AI → LaMa → classic when a requested model is unavailable.
_FALLBACK_CHAIN: dict[ProcessingStrategy, list[ProcessingStrategy]] = {
    ProcessingStrategy.PROPAINTER: [
        ProcessingStrategy.AI_INPAINT,
        ProcessingStrategy.CLASSIC_INPAINT,
    ],
    ProcessingStrategy.STTN: [
        ProcessingStrategy.AI_INPAINT,
        ProcessingStrategy.CLASSIC_INPAINT,
    ],
    ProcessingStrategy.AI_INPAINT: [ProcessingStrategy.CLASSIC_INPAINT],
}


def _plugin_is_available(strategy: ProcessingStrategy, plugin: ProcessingPlugin) -> bool:
    if strategy == ProcessingStrategy.PROPAINTER:
        return propainter_available()
    if strategy == ProcessingStrategy.STTN:
        return sttn_available()
    return bool(plugin.available)


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


def resolve_strategy(
    strategy: ProcessingStrategy | str,
) -> tuple[ProcessingPlugin, ProcessingStrategy, ProcessingStrategy | None]:
    """
    Resolve a strategy plugin, falling back automatically when unavailable.

    Returns (plugin, strategy_used, fallback_from_or_None).
    """
    try:
        requested = (
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

    primary = get_plugin(requested)
    if _plugin_is_available(requested, primary):
        return primary, requested, None

    for candidate in _FALLBACK_CHAIN.get(requested, []):
        plugin = get_plugin(candidate)
        if _plugin_is_available(candidate, plugin):
            return plugin, candidate, requested

    raise AppError(
        code="strategy_unavailable",
        message=(
            f"Strategy '{requested.value}' is unavailable and no fallback "
            "strategy could be resolved"
        ),
        status_code=501,
        details={"requested": requested.value},
    )


def list_strategies() -> list[dict[str, object]]:
    return [
        {
            "name": strategy.value,
            "available": _plugin_is_available(strategy, plugin),
            "fallback": [s.value for s in _FALLBACK_CHAIN.get(strategy, [])],
        }
        for strategy, plugin in _REGISTRY.items()
    ]
