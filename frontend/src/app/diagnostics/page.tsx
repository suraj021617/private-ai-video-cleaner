"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  clearLogs,
  fetchDiagnosticsSummary,
  fetchLogs,
  logsExportUrl,
  refreshModels,
  reportDownloadUrl,
  runBenchmark,
  runExportTest,
  runVideoTest,
  type DiagnosticCheck,
  type ModelInfo,
} from "@/lib/diagnostics";

function statusColor(status: string): string {
  if (status === "ok" || status === "healthy") return "text-emerald-400";
  if (status === "warning" || status === "degraded") return "text-amber-300";
  return "text-rose-400";
}

function statusDot(status: string): string {
  if (status === "ok" || status === "healthy") return "bg-emerald-400";
  if (status === "warning" || status === "degraded") return "bg-amber-300";
  return "bg-rose-400";
}

function Mark({ status }: { status: string }) {
  const ok = status === "ok";
  return (
    <span className={`font-semibold ${statusColor(status)}`}>
      {ok ? "✓ Working" : status === "warning" ? "⚠ Warning" : "✗ Missing"}
    </span>
  );
}

export default function DiagnosticsPage() {
  const [overall, setOverall] = useState("…");
  const [checks, setChecks] = useState<DiagnosticCheck[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [bench, setBench] = useState<Record<string, unknown> | null>(null);
  const [videoTest, setVideoTest] = useState<Record<string, unknown> | null>(
    null,
  );
  const [exportTest, setExportTest] = useState<Record<string, unknown> | null>(
    null,
  );
  const [logs, setLogs] = useState<
    Array<{
      id: string;
      time: string;
      level: string;
      logger: string;
      message: string;
    }>
  >([]);
  const [logSearch, setLogSearch] = useState("");
  const [logLevel, setLogLevel] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    const data = await fetchDiagnosticsSummary();
    setOverall(data.overall);
    setChecks(data.system.checks);
    setModels(data.models.models);
    setUpdatedAt(data.system.generated_at);
  }, []);

  const loadLogs = useCallback(async () => {
    const data = await fetchLogs({
      search: logSearch || undefined,
      level: logLevel || undefined,
    });
    setLogs(data.items);
  }, [logSearch, logLevel]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await loadSummary();
        await loadLogs();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load");
        }
      }
    })();
    const timer = window.setInterval(() => {
      void loadSummary().catch(() => undefined);
    }, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [loadSummary, loadLogs]);

  const chart = useMemo(() => {
    const c = bench?.chart as
      | { labels?: string[]; values?: number[] }
      | undefined;
    if (!c?.labels || !c?.values) return null;
    const max = Math.max(...c.values.map((v) => Number(v) || 0), 1);
    return c.labels.map((label, i) => ({
      label,
      value: Number(c.values?.[i] || 0),
      pct: (Number(c.values?.[i] || 0) / max) * 100,
    }));
  }, [bench]);

  async function run(name: string, fn: () => Promise<void>) {
    setBusy(name);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `${name} failed`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b border-border bg-background/90 px-4 py-3 backdrop-blur sm:px-6">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3">
          <div>
            <p className="font-[family-name:var(--font-display)] text-xs font-bold tracking-wide text-muted">
              Private AI Video Cleaner
            </p>
            <h1 className="font-[family-name:var(--font-display)] text-lg font-extrabold sm:text-xl">
              Production Diagnostics
            </h1>
          </div>
          <div className="flex gap-2">
            <Link
              href="/library"
              className="inline-flex h-10 items-center rounded-xl border border-border px-3 text-sm"
            >
              Library
            </Link>
            <Link
              href="/settings"
              className="inline-flex h-10 items-center rounded-xl border border-border px-3 text-sm"
            >
              Settings
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6">
        <section className="rounded-2xl border border-border bg-surface/80 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={`inline-flex h-3 w-3 rounded-full ${statusDot(overall)}`}
            />
            <p className={`text-sm font-semibold uppercase ${statusColor(overall)}`}>
              System {overall}
            </p>
            {updatedAt ? (
              <p className="text-xs text-muted">Updated {updatedAt}</p>
            ) : null}
            <button
              type="button"
              className="ml-auto h-9 rounded-lg border border-border px-3 text-xs"
              disabled={!!busy}
              onClick={() =>
                void run("refresh", async () => {
                  await loadSummary();
                  await loadLogs();
                })
              }
            >
              Refresh
            </button>
          </div>
          {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}
        </section>

        <section className="space-y-3">
          <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
            System diagnostics
          </h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {checks.map((check) => (
              <div
                key={check.name}
                className="rounded-xl border border-border bg-surface/60 px-3 py-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold">{check.name}</p>
                  <Mark status={check.status} />
                </div>
                <p className="mt-1 text-xs text-muted">{check.detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
              AI model checker
            </h2>
            <button
              type="button"
              disabled={!!busy}
              className="h-9 rounded-lg border border-border px-3 text-xs"
              onClick={() =>
                void run("models", async () => {
                  const res = await refreshModels();
                  setModels(res.models.models);
                })
              }
            >
              {busy === "models" ? "Refreshing…" : "Refresh Models"}
            </button>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {models.map((model) => (
              <div
                key={model.id}
                className="rounded-xl border border-border bg-surface/60 px-3 py-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold">{model.label}</p>
                  <Mark status={model.status} />
                </div>
                <p className="mt-1 text-xs text-muted">{model.detail}</p>
                {model.checksum ? (
                  <p className="mt-1 truncate font-[family-name:var(--font-mono)] text-[10px] text-muted">
                    sha256:{model.checksum.slice(0, 16)}…
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-3 rounded-2xl border border-border bg-surface/70 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
              GPU / CPU benchmark
            </h2>
            <button
              type="button"
              disabled={!!busy}
              className="ml-auto h-9 rounded-lg bg-accent px-3 text-xs font-semibold text-[#041614]"
              onClick={() =>
                void run("bench", async () => {
                  setBench(await runBenchmark());
                })
              }
            >
              {busy === "bench" ? "Running…" : "Run benchmark"}
            </button>
          </div>
          {chart ? (
            <div className="space-y-2">
              {chart.map((row) => (
                <div key={row.label}>
                  <div className="mb-1 flex justify-between text-xs text-muted">
                    <span>{row.label}</span>
                    <span>{row.value}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-surface-elevated">
                    <div
                      className="h-full rounded-full bg-accent transition-[width] duration-500"
                      style={{ width: `${row.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">
              Run a benchmark to measure FPS, memory, and microbench timings.
            </p>
          )}
          {bench?.inference ? (
            <pre className="overflow-x-auto rounded-xl border border-border bg-background/60 p-3 text-xs text-muted">
              {JSON.stringify(bench.inference, null, 2)}
            </pre>
          ) : null}
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3 rounded-2xl border border-border bg-surface/70 p-4">
            <div className="flex items-center gap-2">
              <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
                Video test
              </h2>
              <button
                type="button"
                disabled={!!busy}
                className="ml-auto h-9 rounded-lg border border-border px-3 text-xs"
                onClick={() =>
                  void run("video", async () => {
                    setVideoTest(await runVideoTest());
                  })
                }
              >
                {busy === "video" ? "Testing…" : "One-click test"}
              </button>
            </div>
            {videoTest ? (
              <pre className="max-h-64 overflow-auto rounded-xl border border-border bg-background/60 p-3 text-xs text-muted">
                {JSON.stringify(videoTest, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-muted">
                Generates a sample clip and runs Blur / Fill / Classic / LaMa.
              </p>
            )}
          </div>

          <div className="space-y-3 rounded-2xl border border-border bg-surface/70 p-4">
            <div className="flex items-center gap-2">
              <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
                Export test
              </h2>
              <button
                type="button"
                disabled={!!busy}
                className="ml-auto h-9 rounded-lg border border-border px-3 text-xs"
                onClick={() =>
                  void run("export", async () => {
                    setExportTest(await runExportTest());
                  })
                }
              >
                {busy === "export" ? "Testing…" : "Test exports"}
              </button>
            </div>
            {exportTest ? (
              <pre className="max-h-64 overflow-auto rounded-xl border border-border bg-background/60 p-3 text-xs text-muted">
                {JSON.stringify(exportTest, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-muted">
                Verifies MP4/MOV/MKV, H264/HEVC, audio, FPS, and resolution.
              </p>
            )}
          </div>
        </section>

        <section className="space-y-3 rounded-2xl border border-border bg-surface/70 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
              Health report
            </h2>
            <a
              href={reportDownloadUrl("txt")}
              className="ml-auto h-9 rounded-lg border border-border px-3 text-xs leading-9"
            >
              Save TXT
            </a>
            <a
              href={reportDownloadUrl("json")}
              className="h-9 rounded-lg border border-border px-3 text-xs leading-9"
            >
              Save JSON
            </a>
          </div>
          <p className="text-sm text-muted">
            Report includes system, GPU, models, performance snapshot, errors,
            and warnings.
          </p>
        </section>

        <section className="space-y-3 rounded-2xl border border-border bg-surface/70 p-4">
          <div className="flex flex-wrap items-end gap-2">
            <h2 className="mr-auto font-[family-name:var(--font-display)] text-lg font-bold">
              Log viewer
            </h2>
            <input
              value={logSearch}
              onChange={(e) => setLogSearch(e.target.value)}
              placeholder="Search"
              className="h-9 rounded-lg border border-border bg-background px-2 text-xs"
            />
            <select
              value={logLevel}
              onChange={(e) => setLogLevel(e.target.value)}
              className="h-9 rounded-lg border border-border bg-background px-2 text-xs"
            >
              <option value="">All levels</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
            <button
              type="button"
              className="h-9 rounded-lg border border-border px-3 text-xs"
              onClick={() => void loadLogs()}
            >
              Filter
            </button>
            <button
              type="button"
              className="h-9 rounded-lg border border-border px-3 text-xs"
              onClick={() => {
                void navigator.clipboard.writeText(
                  logs
                    .map(
                      (l) =>
                        `${l.time} | ${l.level} | ${l.logger} | ${l.message}`,
                    )
                    .join("\n"),
                );
              }}
            >
              Copy
            </button>
            <a
              href={logsExportUrl()}
              className="h-9 rounded-lg border border-border px-3 text-xs leading-9"
            >
              Export
            </a>
            <button
              type="button"
              className="h-9 rounded-lg border border-border px-3 text-xs text-danger"
              onClick={() =>
                void run("clear-logs", async () => {
                  await clearLogs();
                  await loadLogs();
                })
              }
            >
              Clear
            </button>
          </div>
          <div className="max-h-80 overflow-auto rounded-xl border border-border bg-background/70 font-[family-name:var(--font-mono)] text-[11px]">
            {logs.length === 0 ? (
              <p className="p-3 text-muted">No log entries.</p>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className="border-b border-border/60 px-3 py-2"
                >
                  <span className={statusColor(log.level.toLowerCase())}>
                    {log.level}
                  </span>{" "}
                  <span className="text-muted">{log.time}</span>{" "}
                  <span className="text-muted">{log.logger}</span>
                  <div>{log.message}</div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
