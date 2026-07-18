"use client";

import { useEffect, useState } from "react";
import {
  createProcessingJob,
  getJobProgress,
  jobDownloadUrl,
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
};

const strategies: { id: ProcessingStrategyName; label: string }[] = [
  { id: "ai_inpaint", label: "AI Inpaint (LaMa)" },
  { id: "classic_inpaint", label: "Classic Inpaint" },
  { id: "blur", label: "Blur" },
  { id: "fill", label: "Fill" },
];

export function ProcessPanel({ videoId, payload, activeMaskId }: Props) {
  const [strategy, setStrategy] =
    useState<ProcessingStrategyName>("ai_inpaint");
  const [exportFormat, setExportFormat] = useState<"mp4" | "mov">("mp4");
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [caps, setCaps] = useState<Caps | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiRequest<Caps>("/api/v1/processing/capabilities", {
          method: "GET",
        });
        if (!cancelled) setCaps(data);
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
        if (next.status === "completed" || next.status === "failed") {
          setBusy(false);
          return;
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
    if (payload.items.length === 0) {
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
          Mask-scoped cleaning. AI Inpaint uses LaMa on the selected region only.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {strategies.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setStrategy(item.id)}
            className={`h-11 rounded-xl px-2 text-xs font-semibold sm:text-sm ${
              strategy === item.id
                ? "bg-accent text-[#041614]"
                : "border border-border"
            }`}
          >
            {item.label}
          </button>
        ))}
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

      <div className="flex gap-2">
        {(["mp4", "mov"] as const).map((fmt) => (
          <button
            key={fmt}
            type="button"
            onClick={() => setExportFormat(fmt)}
            className={`h-10 flex-1 rounded-xl text-sm font-semibold uppercase ${
              exportFormat === fmt
                ? "bg-accent-soft text-accent"
                : "border border-border"
            }`}
          >
            {fmt}
          </button>
        ))}
      </div>

      <button
        type="button"
        disabled={busy}
        onClick={() => void onProcess()}
        className="h-12 w-full rounded-xl bg-accent text-sm font-semibold text-[#041614] disabled:opacity-50"
      >
        {busy ? "Processing…" : "Start processing"}
      </button>

      {progress ? (
        <div>
          <div className="mb-2 flex flex-wrap justify-between gap-2 text-xs text-muted">
            <span>
              {progress.status}
              {progress.device_used ? ` · ${progress.device_used}` : ""}
              {progress.model_loaded ? " · model ready" : ""}
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
