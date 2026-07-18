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
import { ApiError } from "@/lib/api";

type Props = {
  videoId: string;
  payload: SelectionPayload;
  activeMaskId: string | null;
};

const strategies: { id: ProcessingStrategyName; label: string }[] = [
  { id: "classic_inpaint", label: "Classic inpaint" },
  { id: "blur", label: "Blur" },
  { id: "fill", label: "Fill" },
];

export function ProcessPanel({ videoId, payload, activeMaskId }: Props) {
  const [strategy, setStrategy] =
    useState<ProcessingStrategyName>("classic_inpaint");
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
        }, 500);
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
      });
      setJobId(job.id);
    } catch (err) {
      setBusy(false);
      setError(err instanceof ApiError ? err.message : "Failed to start job");
    }
  }

  return (
    <div className="space-y-4 rounded-2xl border border-border bg-surface/90 p-4">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
          Process video
        </h2>
        <p className="mt-1 text-sm text-muted">
          Runs the FFmpeg/OpenCV engine inside your mask only. AI removal is not
          enabled yet.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {strategies.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setStrategy(item.id)}
            className={`h-11 rounded-xl text-sm font-semibold ${
              strategy === item.id
                ? "bg-accent text-[#041614]"
                : "border border-border"
            }`}
          >
            {item.label}
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
          <div className="mb-2 flex justify-between text-xs text-muted">
            <span>
              {progress.status}
              {progress.device_used ? ` · ${progress.device_used}` : ""}
            </span>
            <span>{progress.percent.toFixed(0)}%</span>
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
              Download MP4
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
