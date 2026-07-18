"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { EditorToolbar } from "@/components/editor/EditorToolbar";
import { MaskPanel } from "@/components/editor/MaskPanel";
import { Timeline } from "@/components/editor/Timeline";
import { TransportControls } from "@/components/editor/TransportControls";
import { VideoStage } from "@/components/editor/VideoStage";
import { useSelectionHistory } from "@/hooks/useSelectionHistory";
import { useVideoPlayer } from "@/hooks/useVideoPlayer";
import {
  createEmptyPayload,
  type EditorTool,
  type SelectionPayload,
} from "@/lib/editor/types";
import { videoContentUrl, type Video } from "@/lib/videos";

type Props = {
  video: Video;
};

export function EditorWorkspace({ video }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const fps = video.metadata.fps && video.metadata.fps > 0 ? video.metadata.fps : 30;
  const initialPayload = useMemo(
    () =>
      createEmptyPayload(
        video.metadata.width || 1280,
        video.metadata.height || 720,
        video.metadata.fps,
      ),
    [video],
  );

  const history = useSelectionHistory(initialPayload);
  const player = useVideoPlayer(videoRef);
  const [tool, setTool] = useState<EditorTool>("rect");
  const [brushSize, setBrushSize] = useState(0.035);
  const [showMask, setShowMask] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [activeMaskId, setActiveMaskId] = useState<string | null>(null);
  const [maskName, setMaskName] = useState("Selection mask");

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) history.redo();
        else history.undo();
      }
      if (event.code === "Space") {
        event.preventDefault();
        void player.toggle();
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        player.stepFrames(-1, fps);
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        player.stepFrames(1, fps);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [history, player, fps]);

  return (
    <div className="editor-shell flex min-h-dvh flex-col bg-background">
      <header className="sticky top-0 z-20 border-b border-border bg-background/90 px-4 py-3 backdrop-blur sm:px-6">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="font-[family-name:var(--font-display)] text-xs font-bold tracking-wide text-muted">
              Private AI Video Cleaner
            </p>
            <h1 className="truncate font-[family-name:var(--font-display)] text-lg font-extrabold sm:text-xl">
              {video.original_filename}
            </h1>
          </div>
          <div className="flex shrink-0 gap-2">
            <Link
              href="/library"
              className="inline-flex h-10 items-center rounded-xl border border-border px-3 text-sm"
            >
              Library
            </Link>
            <Link
              href="/upload"
              className="inline-flex h-10 items-center rounded-xl border border-border px-3 text-sm"
            >
              Upload
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6">
        <VideoStage
          videoRef={videoRef}
          src={videoContentUrl(video.id)}
          tool={tool}
          brushSize={brushSize}
          items={history.payload.items}
          currentTime={player.currentTime}
          duration={player.duration || video.metadata.duration_seconds || 0}
          showMask={showMask}
          zoom={zoom}
          onZoomChange={setZoom}
          onAddItem={history.addItem}
        />

        <Timeline
          duration={player.duration || video.metadata.duration_seconds || 0}
          currentTime={player.currentTime}
          fps={fps}
          items={history.payload.items}
          onSeek={player.seek}
        />

        <TransportControls
          playing={player.playing}
          onToggle={() => void player.toggle()}
          onStep={(frames) => player.stepFrames(frames, fps)}
          zoom={zoom}
          onZoomIn={() => setZoom((z) => Math.min(4, Number((z + 0.25).toFixed(2))))}
          onZoomOut={() => setZoom((z) => Math.max(1, Number((z - 0.25).toFixed(2))))}
          disabled={!player.ready}
        />

        <EditorToolbar
          tool={tool}
          brushSize={brushSize}
          showMask={showMask}
          canUndo={history.canUndo}
          canRedo={history.canRedo}
          onToolChange={setTool}
          onBrushSizeChange={setBrushSize}
          onToggleMask={() => setShowMask((v) => !v)}
          onUndo={history.undo}
          onRedo={history.redo}
          onClear={history.clear}
        />

        <div className="rounded-2xl border border-border bg-surface/50 px-4 py-3 text-sm text-muted">
          <p>
            Active mask:{" "}
            <span className="text-foreground">
              {activeMaskId ? maskName : "Unsaved selection"}
            </span>
            {" · "}
            {history.payload.items.length} region
            {history.payload.items.length === 1 ? "" : "s"}
          </p>
          <p className="mt-1 text-xs">
            Tip: pinch to zoom on iPhone, drag timeline to scrub, use −1/+1 for
            frame steps. Space toggles playback.
          </p>
        </div>

        <MaskPanel
          videoId={video.id}
          payload={history.payload}
          activeMaskId={activeMaskId}
          onLoaded={(maskId, payload: SelectionPayload, name) => {
            history.replace(payload);
            setActiveMaskId(maskId);
            setMaskName(name);
          }}
          onSaved={(maskId, name) => {
            setActiveMaskId(maskId || null);
            setMaskName(name);
          }}
        />
      </main>
    </div>
  );
}
