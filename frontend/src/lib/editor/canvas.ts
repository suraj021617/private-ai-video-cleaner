/** Canvas helpers for drawing selection overlays. */

import type { BrushItem, RectItem, SelectionItem } from "./types";

export function itemActiveAt(item: SelectionItem, time: number): boolean {
  return time >= item.start_time - 1e-3 && time <= item.end_time + 1e-3;
}

export function drawSelections(
  ctx: CanvasRenderingContext2D,
  items: SelectionItem[],
  width: number,
  height: number,
  time: number,
  options?: { previewOnly?: boolean; draftRect?: RectItem | null; draftBrush?: BrushItem | null },
) {
  ctx.clearRect(0, 0, width, height);

  // Dim vignette so mask reads clearly
  ctx.fillStyle = "rgba(0,0,0,0.08)";
  ctx.fillRect(0, 0, width, height);

  const active = items.filter((item) => itemActiveAt(item, time));
  for (const item of active) {
    if (item.type === "rect") drawRect(ctx, item, width, height);
    else drawBrush(ctx, item, width, height);
  }

  if (options?.draftRect) drawRect(ctx, options.draftRect, width, height, true);
  if (options?.draftBrush) drawBrush(ctx, options.draftBrush, width, height, true);
}

function drawRect(
  ctx: CanvasRenderingContext2D,
  item: RectItem,
  width: number,
  height: number,
  draft = false,
) {
  const x = item.x * width;
  const y = item.y * height;
  const w = item.w * width;
  const h = item.h * height;
  ctx.fillStyle = draft ? "rgba(61,214,198,0.28)" : "rgba(61,214,198,0.35)";
  ctx.strokeStyle = draft ? "rgba(61,214,198,0.95)" : "rgba(255,255,255,0.85)";
  ctx.lineWidth = draft ? 2 : 1.5;
  ctx.setLineDash(draft ? [6, 4] : []);
  ctx.fillRect(x, y, w, h);
  ctx.strokeRect(x, y, w, h);
  ctx.setLineDash([]);
}

function drawBrush(
  ctx: CanvasRenderingContext2D,
  item: BrushItem,
  width: number,
  height: number,
  draft = false,
) {
  if (item.points.length === 0) return;
  const radius = item.size * Math.min(width, height);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = draft ? "rgba(61,214,198,0.9)" : "rgba(61,214,198,0.75)";
  ctx.fillStyle = draft ? "rgba(61,214,198,0.55)" : "rgba(61,214,198,0.45)";
  ctx.lineWidth = radius * 2;

  if (item.points.length === 1) {
    const p = item.points[0];
    ctx.beginPath();
    ctx.arc(p.x * width, p.y * height, radius, 0, Math.PI * 2);
    ctx.fill();
    return;
  }

  ctx.beginPath();
  ctx.moveTo(item.points[0].x * width, item.points[0].y * height);
  for (let i = 1; i < item.points.length; i += 1) {
    ctx.lineTo(item.points[i].x * width, item.points[i].y * height);
  }
  ctx.stroke();
}

export function formatTimecode(seconds: number, fps = 30): string {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const totalFrames = Math.round(seconds * fps);
  const ff = totalFrames % Math.round(fps);
  const totalSeconds = Math.floor(totalFrames / Math.round(fps));
  const ss = totalSeconds % 60;
  const mm = Math.floor(totalSeconds / 60) % 60;
  const hh = Math.floor(totalSeconds / 3600);
  const pad = (n: number, w = 2) => String(n).padStart(w, "0");
  return hh > 0
    ? `${pad(hh)}:${pad(mm)}:${pad(ss)}.${pad(ff)}`
    : `${pad(mm)}:${pad(ss)}.${pad(ff)}`;
}
