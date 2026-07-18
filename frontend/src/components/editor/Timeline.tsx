"use client";

import { useMemo, useRef, type PointerEvent as ReactPointerEvent } from "react";
import { formatTimecode } from "@/lib/editor/canvas";
import type { SelectionItem } from "@/lib/editor/types";

type Thumb = { time: number; data_url: string };

type Props = {
  duration: number;
  currentTime: number;
  fps: number;
  items: SelectionItem[];
  thumbnails?: Thumb[];
  onSeek: (time: number) => void;
};

export function Timeline({
  duration,
  currentTime,
  fps,
  items,
  thumbnails = [],
  onSeek,
}: Props) {
  const trackRef = useRef<HTMLDivElement>(null);
  const safeDuration = duration > 0 ? duration : 1;
  const progress = Math.min(1, Math.max(0, currentTime / safeDuration));

  const markers = useMemo(
    () =>
      items.map((item) => ({
        id: item.id,
        left: (item.start_time / safeDuration) * 100,
        width: Math.max(
          0.8,
          ((item.end_time - item.start_time) / safeDuration) * 100,
        ),
        kind: item.type,
      })),
    [items, safeDuration],
  );

  const seekFromClientX = (clientX: number) => {
    const track = trackRef.current;
    if (!track) return;
    const rect = track.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    onSeek(ratio * safeDuration);
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    seekFromClientX(event.clientX);
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
    seekFromClientX(event.clientX);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between font-[family-name:var(--font-mono)] text-[11px] text-muted">
        <span>{formatTimecode(currentTime, fps)}</span>
        <span>{formatTimecode(safeDuration, fps)}</span>
      </div>
      {thumbnails.length > 0 ? (
        <div className="flex h-12 overflow-hidden rounded-xl border border-border">
          {thumbnails.map((thumb) => (
            <button
              key={`${thumb.time}-${thumb.data_url.slice(-12)}`}
              type="button"
              className="h-full flex-1 overflow-hidden"
              onClick={() => onSeek(thumb.time)}
              title={formatTimecode(thumb.time, fps)}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={thumb.data_url}
                alt=""
                className="h-full w-full object-cover opacity-90 transition-opacity hover:opacity-100"
              />
            </button>
          ))}
        </div>
      ) : null}
      <div
        ref={trackRef}
        className="relative h-14 touch-none overflow-hidden rounded-xl border border-border bg-surface-elevated"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
      >
        <div className="absolute inset-x-0 top-2 h-8 opacity-80">
          {markers.map((marker) => (
            <div
              key={marker.id}
              className={`absolute top-1 h-6 rounded-sm ${
                marker.kind === "rect"
                  ? "bg-accent/50"
                  : "bg-[rgba(255,180,80,0.55)]"
              }`}
              style={{ left: `${marker.left}%`, width: `${marker.width}%` }}
            />
          ))}
        </div>
        <div
          className="absolute inset-y-0 w-0.5 bg-accent shadow-[0_0_12px_rgba(61,214,198,0.65)] transition-[left] duration-75"
          style={{ left: `calc(${progress * 100}% - 1px)` }}
        />
        <div
          className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[#041614] bg-accent"
          style={{ left: `${progress * 100}%` }}
        />
      </div>
    </div>
  );
}
