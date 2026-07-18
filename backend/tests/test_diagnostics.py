"""Phase 8 production diagnostics tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.diagnostics import (
    collect_model_diagnostics,
    collect_system_diagnostics,
    explain_error,
    report_as_text,
    run_gpu_benchmark,
)
from app.core.config import get_settings
from tests.conftest import bootstrap_and_login


def test_system_diagnostics_has_core_checks() -> None:
    settings = get_settings()
    data = collect_system_diagnostics(settings)
    names = {c["name"] for c in data["checks"]}
    assert "FFmpeg" in names
    assert "FFprobe" in names
    assert "OpenCV" in names
    assert "Python" in names
    assert "Application version" in names
    assert data["overall"] in {"healthy", "degraded", "unhealthy"}


def test_model_diagnostics_includes_builtin_strategies() -> None:
    settings = get_settings()
    data = collect_model_diagnostics(settings)
    ids = {m["id"] for m in data["models"]}
    assert {"blur", "fill", "classic_inpaint", "ai_inpaint", "propainter", "sttn"} <= ids


def test_explain_error_suggests_ffmpeg_fix() -> None:
    help_ = explain_error("ffmpeg_missing: encoder failed")
    assert "FFmpeg" in help_["reason"] or "ffmpeg" in help_["reason"].lower()
    assert help_["suggested_fix"]


def test_benchmark_returns_chart() -> None:
    result = run_gpu_benchmark()
    assert "inference" in result
    assert result["inference"]["frames_per_second"] > 0
    assert "chart" in result


def test_report_text_non_empty() -> None:
    from app.services.diagnostics import build_health_report

    settings = get_settings()
    report = build_health_report(settings)
    text = report_as_text(report)
    assert "Health Report" in text
    assert "System" in text


@pytest.mark.asyncio
async def test_diagnostics_api_requires_auth(app_client: AsyncClient) -> None:
    response = await app_client.get("/api/v1/diagnostics/system")
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_diagnostics_summary_and_logs(app_client: AsyncClient) -> None:
    auth = await bootstrap_and_login(app_client)
    csrf = auth["csrf_token"]
    summary = await app_client.get("/api/v1/diagnostics/summary")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert "system" in body
    assert "models" in body

    logs = await app_client.get("/api/v1/diagnostics/logs")
    assert logs.status_code == 200
    assert "items" in logs.json()

    help_ = await app_client.post(
        "/api/v1/diagnostics/error-help",
        headers={"X-CSRF-Token": csrf},
        json={"message": "torch missing for ai"},
    )
    assert help_.status_code == 200, help_.text
    assert "suggested_fix" in help_.json()


@pytest.mark.asyncio
async def test_diagnostics_benchmark_endpoint(app_client: AsyncClient) -> None:
    auth = await bootstrap_and_login(app_client)
    csrf = auth["csrf_token"]
    response = await app_client.post(
        "/api/v1/diagnostics/benchmark",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200, response.text
    assert "inference" in response.json()
