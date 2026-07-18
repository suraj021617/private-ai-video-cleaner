"""Production diagnostics API — additive, does not alter existing endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, require_auth
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.diagnostics import (
    ErrorHelpOut,
    ErrorHelpRequest,
    LogEntryOut,
    LogsOut,
    ModelRefreshOut,
    ModelsDiagnosticsOut,
    SystemDiagnosticsOut,
)
from app.services import diagnostics as diag
from app.services.log_buffer import attach_log_handler, get_log_handler

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/system", response_model=SystemDiagnosticsOut)
async def diagnostics_system(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> SystemDiagnosticsOut:
    return SystemDiagnosticsOut(**diag.collect_system_diagnostics(settings))


@router.get("/models", response_model=ModelsDiagnosticsOut)
async def diagnostics_models(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> ModelsDiagnosticsOut:
    return ModelsDiagnosticsOut(**diag.collect_model_diagnostics(settings))


@router.post("/models/refresh", response_model=ModelRefreshOut)
async def diagnostics_models_refresh(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> ModelRefreshOut:
    payload = diag.refresh_models(settings)
    return ModelRefreshOut(
        refreshed=payload["refreshed"],
        error=payload.get("error"),
        models=ModelsDiagnosticsOut(**payload["models"]),
    )


@router.post("/benchmark")
async def diagnostics_benchmark(
    auth: AuthContext = Depends(require_auth),
) -> dict:
    return diag.run_gpu_benchmark()


@router.post("/video-test")
async def diagnostics_video_test(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> dict:
    return diag.run_video_strategy_tests(settings)


@router.post("/export-test")
async def diagnostics_export_test(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> dict:
    return diag.run_export_tests(settings)


@router.get("/report")
async def diagnostics_report_json(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> dict:
    return diag.build_health_report(settings)


@router.get("/report.txt")
async def diagnostics_report_txt(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    report = diag.build_health_report(settings)
    return PlainTextResponse(
        diag.report_as_text(report),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="pavc-health-report.txt"'
        },
    )


@router.get("/report.json")
async def diagnostics_report_json_download(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> Response:
    report = diag.build_health_report(settings)
    body = json.dumps(report, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="pavc-health-report.json"'
        },
    )


@router.get("/logs", response_model=LogsOut)
async def diagnostics_logs(
    auth: AuthContext = Depends(require_auth),
    level: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=2000),
) -> LogsOut:
    attach_log_handler()
    items = get_log_handler().list_entries(level=level, search=search, limit=limit)
    return LogsOut(
        items=[LogEntryOut(**i) for i in items],
        total=len(items),
    )


@router.delete("/logs")
async def diagnostics_clear_logs(
    auth: AuthContext = Depends(require_auth),
) -> dict[str, int | str]:
    cleared = get_log_handler().clear()
    return {"status": "cleared", "removed": cleared}


@router.get("/logs/export")
async def diagnostics_export_logs(
    auth: AuthContext = Depends(require_auth),
) -> PlainTextResponse:
    attach_log_handler()
    text = get_log_handler().export_text()
    return PlainTextResponse(
        text or "(no log entries)\n",
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pavc-logs.txt"'},
    )


@router.post("/error-help", response_model=ErrorHelpOut)
async def diagnostics_error_help(
    body: ErrorHelpRequest,
    auth: AuthContext = Depends(require_auth),
) -> ErrorHelpOut:
    return ErrorHelpOut(**diag.explain_error(body.message, body.code))


@router.get("/summary")
async def diagnostics_summary(
    auth: AuthContext = Depends(require_auth),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Dashboard snapshot — system + models (fast)."""
    _ = db  # reserved for future job-error aggregation
    system = diag.collect_system_diagnostics(settings)
    models = diag.collect_model_diagnostics(settings)
    return {
        "system": system,
        "models": models,
        "overall": system["overall"],
    }
