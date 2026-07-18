"use client";

import { useEffect, useState } from "react";
import {
  cancelJob,
  createProcessingJob,
  getJobProgress,
  jobDownloadUrl,
  pauseJob,
  resumeJob,
  type ExportCodec,
  type ExportFormat,
  type ExportQuality,
  type JobProgress,
  type ProcessingStrategyName,
} from "@/lib/jobs";
import type { SelectionPayload } from "@/lib/editor/types";
import { ApiError, apiRequest } from "@/lib/api";

type Props = {
  videoId: string;
  payload: SelectionPayload;
  activeMaskId: string | null;
};

type Caps = {
  selected: string;
  cuda_devices: number;
  lama?: {
    status: string;
    device: string;
    model_loaded: boolean;
    download_bytes?: number;
    download_total?: number | null;
  };
  strategies?: Array<{ name: string; available: boolean; fallback?: string[] }>;
};

const strategies: { id: ProcessingStrategyName; label: string }[] = [
  { id: "ai_inpaint", label: "LaMa" },
  { id: "propainter", label: "ProPainter" },
  { id: "sttn", label: "STTN" },
  { id: "classic_inpaint", label: "Classic" },
  { id: "blur", label: "Blur" },
  { id: "fill", label: "Fill" },
];

export function ProcessPanel({ videoId, payload, activeMaskId }: Props) {
  const [strategy, setStrategy] =
    useState<ProcessingStrategyName>("classic_inpaint");
  const [exportFormat, setExportFormat] = useState<ExportFormat>("mp4");
  const [exportCodec, setExportCodec] = useState<ExportCodec>("h264");
  const [exportQuality, setExportQuality] =
    useState<ExportQuality>("balanced");
  const [export4k, setExport4k] = useState(false);
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [caps, setCaps] = useState<Caps | null>(null);
  const [liteMode, setLiteMode] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [data, health] = await Promise.all([
          apiRequest<Caps>("/api/v1/processing/capabilities", {
            method: "GET",
          }),
          apiRequest<{ lite_mode?: boolean }>("/api/v1/health", {
            method: "GET",
          }),
        ]);
        if (cancelled) return;
        setCaps(data);
        const lite = Boolean(health.lite_mode);
        setLiteMode(lite);
        if (!lite) {
          setStrategy("ai_inpaint");
        }
      } catch {
        /* optional */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const next = await getJobProgress(jobId);
        if (cancelled) return;
        setProgress(next);
        if (
          next.status === "completed" ||
          next.status === "failed" ||
          next.status === "cancelled"
        ) {
          setBusy(false);
          return;
        }
        if (next.status === "paused") {
          setBusy(false);
        }
        window.setTimeout(() => {
          void tick();
        }, 400);
      } catch (err) {
        if (!cancelled) {
          setBusy(false);
          setError(err instanceof ApiError ? err.message : "Progress failed");
        }
      }
    };
    void tick();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  async function onProcess() {
    if (payload.items.length === 0 && !(payload.masks || []).length) {
      setError("Draw a selection mask before processing.");
      return;
    }
    setBusy(true);
    setError(null);
    setProgress(null);
    try {
      const job = await createProcessingJob(videoId, {
        strategy,
        mask_id: activeMaskId,
        payload,
        prefer_gpu: true,
        export_format: exportFormat,
        export_codec: exportCodec,
        export_quality: exportQuality,
        export_width: export4k ? 3840 : null,
        export_height: export4k ? 2160 : null,
        feather_radius: payload.feather ?? 12,
        mask_expansion: payload.expansion ?? 0,
        edge_refine: payload.edge_refine ?? 0,
      });
      setJobId(job.id);
    } catch (err) {
      setBusy(false);
      setError(err instanceof ApiError ? err.message : "Failed to start job");
    }
  }

  const downloadPct =
    caps?.lama?.download_total && caps.lama.download_total > 0
      ? Math.min(
          100,
          Math.round(
            ((caps.lama.download_bytes ?? 0) / caps.lama.download_total) * 100,
          ),
        )
      : null;

  return (
    <div className="space-y-4 rounded-2xl border border-border bg-surface/90 p-4">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
          Process video
        </h2>
        <p className="mt-1 text-sm text-muted">
          {liteMode
            ? "Lite mode: Classic / Blur / Fill (no AI model required)."
            : "Advanced AI falls back automatically when a model is unavailable."}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {(liteMode
          ? strategies.filter((s) =>
              ["classic_inpaint", "blur", "fill"].includes(s.id),
            )
          : strategies
        ).map((item) => {
          const meta = caps?.strategies?.find((s) => s.name === item.id);
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setStrategy(item.id)}
              className={`h-11 rounded-xl px-2 text-xs font-semibold sm:text-sm ${
                strategy === item.id
                  ? "bg-accent text-[#041614]"
                  : "border border-border"
              }`}
              title={
                meta && !meta.available
                  ? `Unavailable — fallback: ${(meta.fallback || []).join(", ") || "classic"}`
                  : undefined
              }
            >
              {item.label}
              {meta && !meta.available ? " *" : ""}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-2 text-xs text-muted">
        <span className="rounded-lg border border-border px-2 py-1">
          Device: {caps?.lama?.device || caps?.selected || "…"}
        </span>
        <span className="rounded-lg border border-border px-2 py-1">
          GPU: {(caps?.cuda_devices ?? 0) > 0 ? "available" : "fallback CPU"}
        </span>
        <span className="rounded-lg border border-border px-2 py-1">
          Model:{" "}
          {caps?.lama?.model_loaded
            ? "loaded"
            : caps?.lama?.status === "downloading"
              ? `downloading${downloadPct != null ? ` ${downloadPct}%` : ""}`
              : caps?.lama?.status || "not loaded"}
        </span>
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <label className="text-xs text-muted">
          Container
          <select
            className="mt-1 h-10 w-full rounded-xl border border-border bg-background px-2 text-sm text-foreground"
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
          >
            <option value="mp4">MP4</option>
            <option value="mov">MOV</option>
            <option value="mkv">MKV</option>
          </select>
        </label>
        <label className="text-xs text-muted">
          Codec
          <select
            className="mt-1 h-10 w-full rounded-xl border border-border bg-background px-2 text-sm text-foreground"
            value={exportCodec}
            onChange={(e) => setExportCodec(e.target.value as ExportCodec)}
          >
            <option value="h264">H.264</option>
            <option value="hevc">HEVC</option>
          </select>
        </label>
        <label className="text-xs text-muted">
          Quality
          <select
            className="mt-1 h-10 w-full rounded-xl border border-border bg-background px-2 text-sm text-foreground"
            value={exportQuality}
            onChange={(e) => setExportQuality(e.target.value as ExportQuality)}
          >
            <option value="fast">Fast</option>
            <option value="balanced">Balanced</option>
            <option value="best">Best</option>
          </select>
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={export4k}
          onChange={(e) => setExport4k(e.target.checked)}
        />
        Export at 4K (3840×2160)
      </label>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void onProcess()}
          className="h-12 min-w-[10rem] flex-1 rounded-xl bg-accent text-sm font-semibold text-[#041614] disabled:opacity-50"
        >
          {busy ? "Processing…" : "Start processing"}
        </button>
        {jobId && progress?.status === "running" ? (
          <button
            type="button"
            className="h-12 rounded-xl border border-border px-4 text-sm"
            onClick={() => void pauseJob(jobId)}
          >
            Pause
          </button>
        ) : null}
        {jobId && progress?.status === "paused" ? (
          <button
            type="button"
            className="h-12 rounded-xl border border-border px-4 text-sm"
            onClick={() => {
              setBusy(true);
              void resumeJob(jobId);
            }}
          >
            Resume
          </button>
        ) : null}
        {jobId &&
        progress &&
        !["completed", "failed", "cancelled"].includes(progress.status) ? (
          <button
            type="button"
            className="h-12 rounded-xl border border-border px-4 text-sm text-danger"
            onClick={() => void cancelJob(jobId)}
          >
            Cancel
          </button>
        ) : null}
      </div>

      {progress ? (
        <div>
          <div className="mb-2 flex flex-wrap justify-between gap-2 text-xs text-muted">
            <span>
              {progress.status}
              {progress.device_used ? ` · ${progress.device_used}` : ""}
              {progress.strategy_used
                ? ` · ${progress.strategy_used}`
                : ""}
              {progress.fallback_from
                ? ` (from ${progress.fallback_from})`
                : ""}
            </span>
            <span>
              {progress.frames_done}/{progress.frames_total || "?"} frames
              {progress.fps != null ? ` · ${progress.fps} FPS` : ""}
              {progress.eta_seconds != null
                ? ` · ETA ${progress.eta_seconds}s`
                : ""}
              {" · "}
              {progress.percent.toFixed(0)}%
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-elevated">
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-300"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
          {progress.message ? (
            <p className="mt-2 text-xs text-muted">{progress.message}</p>
          ) : null}
          {progress.status === "completed" && jobId ? (
            <a
              href={jobDownloadUrl(jobId)}
              className="mt-3 inline-flex h-11 items-center rounded-xl border border-border px-4 text-sm"
            >
              Download {exportFormat.toUpperCase()}
            </a>
          ) : null}
          {progress.error ? (
            <p className="mt-2 text-sm text-danger">{progress.error}</p>
          ) : null}
        </div>
      ) : null}

      {error ? <p className="text-sm text-danger">{error}</p> : null}
    </div>
  );
}
