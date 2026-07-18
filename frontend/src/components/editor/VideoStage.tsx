"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { drawSelections } from "@/lib/editor/canvas";
import {
  newId,
  type BrushItem,
  type EditorTool,
  type RectItem,
  type SelectionItem,
} from "@/lib/editor/types";

type Props = {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  src: string;
  tool: EditorTool;
  brushSize: number;
  items: SelectionItem[];
  currentTime: number;
  duration: number;
  showMask: boolean;
  zoom: number;
  onZoomChange: (zoom: number) => void;
  onAddItem: (item: SelectionItem) => void;
};

type Point = { x: number; y: number };

export function VideoStage({
  videoRef,
  src,
  tool,
  brushSize,
  items,
  currentTime,
  duration,
  showMask,
  zoom,
  onZoomChange,
  onAddItem,
}: Props) {
  const stageRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [draftRect, setDraftRect] = useState<RectItem | null>(null);
  const [draftBrush, setDraftBrush] = useState<BrushItem | null>(null);
  const dragRef = useRef<{
    mode: "rect" | "brush" | "pan";
    origin: Point;
    lastPan: Point;
    pointerId: number;
  } | null>(null);
  const pinchRef = useRef<{ distance: number; zoom: number } | null>(null);

  const resizeCanvas = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const rect = video.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (showMask) {
      drawSelections(ctx, items, rect.width, rect.height, currentTime, {
        draftRect,
        draftBrush,
      });
    } else {
      ctx.clearRect(0, 0, rect.width, rect.height);
    }
  }, [videoRef, items, currentTime, showMask, draftRect, draftBrush]);

  useEffect(() => {
    resizeCanvas();
    const observer = new ResizeObserver(() => resizeCanvas());
    if (videoRef.current) observer.observe(videoRef.current);
    window.addEventListener("orientationchange", resizeCanvas);
    return () => {
      observer.disconnect();
      window.removeEventListener("orientationchange", resizeCanvas);
    };
  }, [resizeCanvas, videoRef]);

  const toNormalized = (clientX: number, clientY: number): Point | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    return {
      x: Math.min(1, Math.max(0, (clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (clientY - rect.top) / rect.height)),
    };
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    if (event.pointerType === "touch" && event.nativeEvent.isPrimary === false) {
      return;
    }
    const point = toNormalized(event.clientX, event.clientY);
    if (!point) return;
    event.currentTarget.setPointerCapture(event.pointerId);

    if (tool === "pan") {
      dragRef.current = {
        mode: "pan",
        origin: { x: event.clientX, y: event.clientY },
        lastPan: pan,
        pointerId: event.pointerId,
      };
      return;
    }

    if (tool === "rect") {
      dragRef.current = {
        mode: "rect",
        origin: point,
        lastPan: pan,
        pointerId: event.pointerId,
      };
      setDraftRect({
        id: "draft",
        type: "rect",
        x: point.x,
        y: point.y,
        w: 0.001,
        h: 0.001,
        start_time: 0,
        end_time: duration || 0,
      });
      return;
    }

    dragRef.current = {
      mode: "brush",
      origin: point,
      lastPan: pan,
      pointerId: event.pointerId,
    };
    setDraftBrush({
      id: "draft",
      type: "brush",
      points: [point],
      size: brushSize,
      start_time: 0,
      end_time: duration || 0,
    });
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    if (drag.mode === "pan") {
      setPan({
        x: drag.lastPan.x + (event.clientX - drag.origin.x),
        y: drag.lastPan.y + (event.clientY - drag.origin.y),
      });
      return;
    }

    const point = toNormalized(event.clientX, event.clientY);
    if (!point) return;

    if (drag.mode === "rect") {
      const x = Math.min(drag.origin.x, point.x);
      const y = Math.min(drag.origin.y, point.y);
      const w = Math.abs(point.x - drag.origin.x);
      const h = Math.abs(point.y - drag.origin.y);
      setDraftRect({
        id: "draft",
        type: "rect",
        x,
        y,
        w: Math.max(w, 0.001),
        h: Math.max(h, 0.001),
        start_time: 0,
        end_time: duration || 0,
      });
      return;
    }

    setDraftBrush((prev) =>
      prev
        ? {
            ...prev,
            points: [...prev.points, point],
          }
        : prev,
    );
  };

  const finishDrag = (event: ReactPointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;

    if (drag.mode === "rect" && draftRect && draftRect.w > 0.008 && draftRect.h > 0.008) {
      onAddItem({ ...draftRect, id: newId("rect") });
    }
    if (drag.mode === "brush" && draftBrush && draftBrush.points.length > 0) {
      onAddItem({ ...draftBrush, id: newId("brush") });
    }
    setDraftRect(null);
    setDraftBrush(null);
  };

  const onTouchStart = (event: React.TouchEvent<HTMLDivElement>) => {
    if (event.touches.length === 2) {
      const [a, b] = [event.touches[0], event.touches[1]];
      const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      pinchRef.current = { distance, zoom };
      dragRef.current = null;
    }
  };

  const onTouchMove = (event: React.TouchEvent<HTMLDivElement>) => {
    if (event.touches.length === 2 && pinchRef.current) {
      event.preventDefault();
      const [a, b] = [event.touches[0], event.touches[1]];
      const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      const ratio = distance / pinchRef.current.distance;
      const next = Math.min(4, Math.max(1, pinchRef.current.zoom * ratio));
      onZoomChange(Number(next.toFixed(2)));
    }
  };

  const onTouchEnd = () => {
    if (!window || (window as Window & { TouchEvent?: unknown }).TouchEvent === undefined) {
      pinchRef.current = null;
      return;
    }
    pinchRef.current = null;
  };

  return (
    <div
      ref={stageRef}
      className="relative flex min-h-[240px] flex-1 items-center justify-center overflow-hidden rounded-2xl bg-[#050608] touch-none"
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
    >
      <div
        className="relative inline-block max-h-full max-w-full transition-transform duration-150 ease-out"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: "center center",
        }}
      >
        <video
          ref={videoRef}
          src={src}
          playsInline
          preload="auto"
          className="max-h-[min(52vh,480px)] w-auto max-w-full select-none rounded-lg bg-black object-contain sm:max-h-[min(58vh,620px)]"
          controls={false}
        />
        <canvas
          ref={canvasRef}
          className="absolute inset-0 h-full w-full touch-none"
          style={{ cursor: tool === "pan" ? "grab" : "crosshair" }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={finishDrag}
          onPointerCancel={finishDrag}
        />
      </div>
    </div>
  );
}
