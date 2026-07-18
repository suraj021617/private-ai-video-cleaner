"use client";

import { useRef, useState } from "react";
import {
  uploadVideo,
  type UploadProgress,
  type Video,
} from "@/lib/videos";
import { ApiError } from "@/lib/api";

type Props = {
  onUploaded: (video: Video) => void;
};

export function VideoUploader({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onFileChange(file: File | null) {
    if (!file) return;
    setBusy(true);
    setError(null);
    setProgress(null);
    try {
      const video = await uploadVideo(file, setProgress);
      onUploaded(video);
      setProgress(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      setError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-surface/80 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
            Upload video
          </h2>
          <p className="mt-1 text-sm text-muted">
            MP4, MOV, M4V, WebM, or MKV. Only media you may edit.
          </p>
        </div>
        <label className="inline-flex h-11 cursor-pointer items-center justify-center rounded-lg bg-accent px-5 text-sm font-semibold text-[#041614] transition hover:brightness-110">
          {busy ? "Uploading…" : "Choose file"}
          <input
            ref={inputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/webm,video/x-matroska,.mp4,.mov,.m4v,.webm,.mkv"
            className="hidden"
            disabled={busy}
            onChange={(e) => void onFileChange(e.target.files?.[0] ?? null)}
          />
        </label>
      </div>

      {progress ? (
        <div className="mt-5">
          <div className="mb-2 flex justify-between text-xs text-muted">
            <span className="uppercase tracking-[0.14em]">{progress.status}</span>
            <span>{progress.percent.toFixed(0)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-elevated">
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-300"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
        </div>
      ) : null}

      {error ? <p className="mt-4 text-sm text-danger">{error}</p> : null}
    </div>
  );
}
