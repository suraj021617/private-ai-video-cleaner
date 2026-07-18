"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api";
import {
  detectObjects,
  refineMaskPreview,
  trackObject,
} from "@/lib/smartEdit";
import type { RectItem, SelectionPayload } from "@/lib/editor/types";

type Props = {
  videoId: string;
  payload: SelectionPayload;
  currentTime: number;
  onPayloadChange: (payload: SelectionPayload) => void;
  onAddItems: (items: RectItem[]) => void;
};

export function SmartEditPanel({
  videoId,
  payload,
  currentTime,
  onPayloadChange,
  onAddItems,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  async function onDetect() {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const result = await detectObjects(videoId, currentTime);
      onAddItems(result.items as RectItem[]);
      setStatus(`Detected ${result.objects.length} object proposal(s)`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Detect failed");
    } finally {
      setBusy(false);
    }
  }

  async function onTrackSelected() {
    const rect = [...payload.items]
      .reverse()
      .find((item): item is RectItem => item.type === "rect");
    if (!rect) {
      setError("Draw or detect a rectangle first.");
      return;
    }
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const result = await trackObject(videoId, {
        start_time: currentTime,
        x: rect.x,
        y: rect.y,
        w: rect.w,
        h: rect.h,
      });
      const end =
        result.keyframes.length > 0
          ? result.keyframes[result.keyframes.length - 1].time
          : rect.end_time;
      const nextItems = payload.items.map((item) =>
        item.id === rect.id
          ? {
              ...rect,
              keyframes: result.keyframes,
              start_time: Math.min(rect.start_time, currentTime),
              end_time: Math.max(end, rect.end_time),
            }
          : item,
      );
      onPayloadChange({ ...payload, items: nextItems });
      setStatus(`Tracked ${result.keyframes.length} keyframe(s)`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Track failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRefinePreview() {
    setBusy(true);
    setError(null);
    try {
      const result = await refineMaskPreview(videoId, payload, currentTime);
      setPreviewUrl(`data:image/png;base64,${result.mask_png_base64}`);
      setStatus("Mask refine preview ready");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Refine failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 rounded-2xl border border-border bg-surface/90 p-4">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-lg font-bold">
          Smart AI editing
        </h2>
        <p className="mt-1 text-sm text-muted">
          Detect objects, track across frames, and refine mask edges locally.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <label className="text-xs text-muted">
          Feather
          <input
            type="range"
            min={0}
            max={48}
            value={payload.feather ?? 0}
            onChange={(e) =>
              onPayloadChange({
                ...payload,
                feather: Number(e.target.value),
              })
            }
            className="mt-1 w-full"
          />
        </label>
        <label className="text-xs text-muted">
          Expansion
          <input
            type="range"
            min={0}
            max={32}
            value={payload.expansion ?? 0}
            onChange={(e) =>
              onPayloadChange({
                ...payload,
                expansion: Number(e.target.value),
              })
            }
            className="mt-1 w-full"
          />
        </label>
        <label className="text-xs text-muted">
          Edge refine
          <input
            type="range"
            min={0}
            max={8}
            value={payload.edge_refine ?? 0}
            onChange={(e) =>
              onPayloadChange({
                ...payload,
                edge_refine: Number(e.target.value),
              })
            }
            className="mt-1 w-full"
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void onDetect()}
          className="h-10 rounded-xl border border-border px-3 text-sm disabled:opacity-50"
        >
          Auto-detect
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void onTrackSelected()}
          className="h-10 rounded-xl border border-border px-3 text-sm disabled:opacity-50"
        >
          Track selection
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void onRefinePreview()}
          className="h-10 rounded-xl border border-border px-3 text-sm disabled:opacity-50"
        >
          Refine preview
        </button>
      </div>

      {previewUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={previewUrl}
          alt="Refined mask preview"
          className="h-24 w-auto rounded-lg border border-border"
        />
      ) : null}
      {status ? <p className="text-xs text-muted">{status}</p> : null}
      {error ? <p className="text-sm text-danger">{error}</p> : null}
    </div>
  );
}
