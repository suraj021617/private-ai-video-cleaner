"""Application settings API for LaMa / processing preferences."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, require_auth
from app.core.config import Settings, get_settings
from app.processing.plugins.lama import get_model_manager
from app.schemas.job import AppSettingsOut, AppSettingsUpdate
from app.services.runtime_settings import get_app_settings, save_runtime_overrides

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettingsOut)
async def read_settings(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> AppSettingsOut:
    return get_app_settings(settings)


@router.put("", response_model=AppSettingsOut)
async def update_settings(
    payload: AppSettingsUpdate,
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> AppSettingsOut:
    return save_runtime_overrides(payload, settings)


@router.get("/lama-status")
async def lama_status(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> dict:
    from app.services.runtime_settings import apply_runtime_overrides

    effective = apply_runtime_overrides(settings)
    manager = get_model_manager(
        effective.lama_model_dir, prefer_gpu=effective.lama_prefer_gpu
    )
    return manager.status


@router.post("/lama-ensure")
async def lama_ensure_model(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> dict:
    from app.services.runtime_settings import apply_runtime_overrides

    effective = apply_runtime_overrides(settings)
    manager = get_model_manager(
        effective.lama_model_dir, prefer_gpu=effective.lama_prefer_gpu
    )
    manager.ensure_model(prefer_gpu=effective.lama_prefer_gpu)
    return manager.status
