"""Persisted runtime settings overlay (Settings page)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from app.core.config import Settings, get_settings
from app.schemas.job import AppSettingsOut, AppSettingsUpdate

_LOCK = threading.Lock()


def _settings_path(settings: Settings) -> Path:
    path = Path(settings.storage_root) / "app_settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_runtime_overrides(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    path = _settings_path(settings)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_runtime_overrides(update: AppSettingsUpdate, settings: Settings | None = None) -> AppSettingsOut:
    settings = settings or get_settings()
    with _LOCK:
        current = load_runtime_overrides(settings)
        data = update.model_dump(exclude_none=True)
        current.update(data)
        path = _settings_path(settings)
        path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        # Invalidate settings cache so new env-backed defaults refresh if needed
        get_settings.cache_clear()
        return get_app_settings()


def apply_runtime_overrides(settings: Settings) -> Settings:
    """Return a Settings copy-like object with runtime overrides applied."""
    overrides = load_runtime_overrides(settings)
    if not overrides:
        return settings
    values = settings.model_dump()
    mapping = {
        "lama_model_dir": "lama_model_dir",
        "lama_prefer_gpu": "lama_prefer_gpu",
        "lama_cpu_threads": "lama_cpu_threads",
        "lama_padding": "lama_padding",
        "lama_blend_strength": "lama_blend_strength",
        "lama_feather_radius": "lama_feather_radius",
        "processing_temp_dir": "processing_temp_dir",
    }
    for key, field in mapping.items():
        if key in overrides and overrides[key] is not None:
            values[field] = overrides[key]
    return Settings(**values)


def get_app_settings(settings: Settings | None = None) -> AppSettingsOut:
    base = settings or get_settings()
    effective = apply_runtime_overrides(base)
    return AppSettingsOut(
        lama_model_dir=str(effective.lama_model_dir),
        lama_prefer_gpu=bool(effective.lama_prefer_gpu),
        lama_cpu_threads=int(effective.lama_cpu_threads),
        lama_padding=int(effective.lama_padding),
        lama_blend_strength=float(effective.lama_blend_strength),
        lama_feather_radius=int(effective.lama_feather_radius),
        processing_temp_dir=str(effective.temp_dir),
        storage_root=str(effective.storage_root),
    )
