import { apiRequest } from "@/lib/api";
import { apiConfig } from "@/lib/config";

export type CheckStatus = "ok" | "warning" | "error" | "missing";

export type DiagnosticCheck = {
  name: string;
  status: CheckStatus | string;
  ok: boolean;
  detail: string;
  value?: unknown;
};

export type SystemDiagnostics = {
  generated_at: string;
  overall: string;
  counts: { ok: number; warning: number; error: number };
  checks: DiagnosticCheck[];
};

export type ModelInfo = {
  id: string;
  label: string;
  exists: boolean;
  readable: boolean;
  compatible: boolean;
  corrupted: boolean;
  checksum: string | null;
  path: string | null;
  status: string;
  detail: string;
};

export async function fetchDiagnosticsSummary(): Promise<{
  overall: string;
  system: SystemDiagnostics;
  models: { models: ModelInfo[]; generated_at: string };
}> {
  return apiRequest("/api/v1/diagnostics/summary", { method: "GET" });
}

export async function fetchSystemDiagnostics(): Promise<SystemDiagnostics> {
  return apiRequest("/api/v1/diagnostics/system", { method: "GET" });
}

export async function fetchModelsDiagnostics(): Promise<{
  models: ModelInfo[];
  generated_at: string;
}> {
  return apiRequest("/api/v1/diagnostics/models", { method: "GET" });
}

export async function refreshModels(): Promise<{
  refreshed: boolean;
  error: string | null;
  models: { models: ModelInfo[] };
}> {
  return apiRequest("/api/v1/diagnostics/models/refresh", { method: "POST" });
}

export async function runBenchmark(): Promise<Record<string, unknown>> {
  return apiRequest("/api/v1/diagnostics/benchmark", { method: "POST" });
}

export async function runVideoTest(): Promise<Record<string, unknown>> {
  return apiRequest("/api/v1/diagnostics/video-test", { method: "POST" });
}

export async function runExportTest(): Promise<Record<string, unknown>> {
  return apiRequest("/api/v1/diagnostics/export-test", { method: "POST" });
}

export async function fetchLogs(params?: {
  level?: string;
  search?: string;
}): Promise<{
  items: Array<{
    id: string;
    time: string;
    level: string;
    logger: string;
    message: string;
  }>;
  total: number;
}> {
  const q = new URLSearchParams();
  if (params?.level) q.set("level", params.level);
  if (params?.search) q.set("search", params.search);
  const suffix = q.toString() ? `?${q}` : "";
  return apiRequest(`/api/v1/diagnostics/logs${suffix}`, { method: "GET" });
}

export async function clearLogs(): Promise<{ removed: number }> {
  return apiRequest("/api/v1/diagnostics/logs", { method: "DELETE" });
}

export async function explainError(input: {
  message?: string;
  code?: string;
}): Promise<{
  reason: string;
  suggested_fix: string;
  matched: string | null;
}> {
  return apiRequest("/api/v1/diagnostics/error-help", { json: input });
}

export function reportDownloadUrl(format: "txt" | "json"): string {
  return `${apiConfig.baseUrl}/api/v1/diagnostics/report.${format}`;
}

export function logsExportUrl(): string {
  return `${apiConfig.baseUrl}/api/v1/diagnostics/logs/export`;
}
