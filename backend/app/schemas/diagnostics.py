"""Diagnostics request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DiagnosticCheck(BaseModel):
    name: str
    status: str
    ok: bool
    detail: str
    value: Any = None


class SystemDiagnosticsOut(BaseModel):
    generated_at: str
    overall: str
    counts: dict[str, int]
    checks: list[DiagnosticCheck]
    capabilities: dict[str, Any] = Field(default_factory=dict)


class ModelInfoOut(BaseModel):
    id: str
    label: str
    exists: bool
    readable: bool
    compatible: bool
    corrupted: bool
    checksum: str | None = None
    path: str | None = None
    status: str
    detail: str


class ModelsDiagnosticsOut(BaseModel):
    generated_at: str
    models: list[ModelInfoOut]
    strategies: list[dict[str, Any]] = Field(default_factory=list)
    lama_manager: dict[str, Any] | None = None


class ModelRefreshOut(BaseModel):
    refreshed: bool
    error: str | None = None
    models: ModelsDiagnosticsOut


class ErrorHelpRequest(BaseModel):
    message: str | None = None
    code: str | None = None


class ErrorHelpOut(BaseModel):
    reason: str
    suggested_fix: str
    matched: str | None = None
    original: str | None = None
    code: str | None = None


class LogEntryOut(BaseModel):
    id: str
    time: str
    level: str
    logger: str
    message: str


class LogsOut(BaseModel):
    items: list[LogEntryOut]
    total: int
