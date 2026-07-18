"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { EditorToolbar } from "@/components/editor/EditorToolbar";
import { MaskPanel } from "@/components/editor/MaskPanel";
import { ProcessPanel } from "@/components/editor/ProcessPanel";
import { SmartEditPanel } from "@/components/editor/SmartEditPanel";
import { Timeline } from "@/components/editor/Timeline";
import { TransportControls } from "@/components/editor/TransportControls";
import { VideoStage } from "@/components/editor/VideoStage";
import { useSelectionHistory } from "@/hooks/useSelectionHistory";
import { useVideoPlayer } from "@/hooks/useVideoPlayer";
import {
  createEmptyPayload,
  type EditorTool,
  type RectItem,
  type SelectionPayload,
} from "@/lib/editor/types";
import { createProject, updateProject } from "@/lib/projects";
import { fetchTimelineThumbnails } from "@/lib/smartEdit";
import { videoContentUrl, type Video } from "@/lib/videos";

type Props = {
  video: Video;
};

type PreviewMode = "before" | "after" | "split";

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

  const history = useSelectionHistory(initialPayload, video.id);
  const player = useVideoPlayer(videoRef);
  const [tool, setTool] = useState<EditorTool>("rect");
  const [brushSize, setBrushSize] = useState(0.035);
  const [showMask, setShowMask] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [activeMaskId, setActiveMaskId] = useState<string | null>(null);
  const [maskName, setMaskName] = useState("Selection mask");
  const [previewMode, setPreviewMode] = useState<PreviewMode>("before");
  const [thumbs, setThumbs] = useState<
    Array<{ time: number; data_url: string }>
  >([]);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [autosaveNote, setAutosaveNote] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
        return;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) history.redo();
        else history.undo();
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        void persistProject();
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
      if (event.key.toLowerCase() === "b") setPreviewMode("before");
      if (event.key.toLowerCase() === "a") setPreviewMode("after");
      if (event.key.toLowerCase() === "s" && !event.metaKey && !event.ctrlKey) {
        setPreviewMode("split");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [history, player, fps]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchTimelineThumbnails(video.id, 10);
        if (!cancelled) setThumbs(data.thumbnails);
      } catch {
        /* optional */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [video.id]);

  // Autosave project every 20s
  useEffect(() => {
    const timer = window.setInterval(() => {
      void persistProject(true);
    }, 20000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [history.payload, projectId, zoom, player.currentTime]);

  async function persistProject(silent = false) {
    const body = {
      name: `${video.original_filename} project`,
      video_id: video.id,
      payload: {
        version: 1,
        video_id: video.id,
        selection: history.payload,
        timeline: { zoom, current_time: player.currentTime },
        settings: {
          feather: history.payload.feather ?? 0,
          expansion: history.payload.expansion ?? 0,
          edge_refine: history.payload.edge_refine ?? 0,
          strategy: "ai_inpaint",
        },
        undo_stack: history.past?.slice(-20) ?? [],
        redo_stack: history.future?.slice(-20) ?? [],
        ai_selections: [],
      },
    };
    try {
      if (projectId) {
        await updateProject(projectId, {
          name: body.name,
          payload: body.payload,
        });
      } else {
        const created = await createProject(body);
        setProjectId(created.id);
      }
      if (!silent) setAutosaveNote("Project saved");
      else setAutosaveNote("Autosaved");
    } catch {
      if (!silent) setAutosaveNote("Project save failed");
    }
  }

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
            <button
              type="button"
              onClick={() => void persistProject()}
              className="inline-flex h-10 items-center rounded-xl border border-border px-3 text-sm"
            >
              Save project
            </button>
            <Link
              href="/library"
              className="inline-flex h-10 items-center rounded-xl border border-border px-3 text-sm"
            >
              Library
            </Link>
            <Link
              href="/diagnostics"
              className="inline-flex h-10 items-center rounded-xl border border-border px-3 text-sm"
            >
              Diagnostics
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

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-4 px-4 py-4 sm:px-6 sm:py-6">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {(
            [
              ["before", "Before"],
              ["after", "After (mask)"],
              ["split", "Split"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setPreviewMode(id)}
              className={`h-8 rounded-lg px-3 ${
                previewMode === id
                  ? "bg-accent text-[#041614]"
                  : "border border-border"
              }`}
            >
              {label}
            </button>
          ))}
          {autosaveNote ? (
            <span className="ml-auto text-muted">{autosaveNote}</span>
          ) : null}
        </div>

        <div className="relative">
          <VideoStage
            videoRef={videoRef}
            src={videoContentUrl(video.id)}
            tool={tool}
            brushSize={brushSize}
            items={history.payload.items}
            currentTime={player.currentTime}
            duration={player.duration || video.metadata.duration_seconds || 0}
            showMask={previewMode !== "before" && showMask}
            zoom={zoom}
            onZoomChange={setZoom}
            onAddItem={history.addItem}
          />
          {previewMode === "split" ? (
            <div className="pointer-events-none absolute inset-y-3 right-3 flex w-1/2 items-start justify-end">
              <div className="rounded-lg border border-accent/40 bg-background/70 px-2 py-1 text-[11px] text-accent backdrop-blur">
                Split · mask on left / clean right cue
              </div>
            </div>
          ) : null}
        </div>

        <Timeline
          duration={player.duration || video.metadata.duration_seconds || 0}
          currentTime={player.currentTime}
          fps={fps}
          items={history.payload.items}
          thumbnails={thumbs}
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
            {" · "}
            feather {history.payload.feather ?? 0} / expand{" "}
            {history.payload.expansion ?? 0}
          </p>
          <p className="mt-1 text-xs">
            Shortcuts: Space play, ←/→ frame, Ctrl/Cmd+Z undo, Ctrl/Cmd+S save,
            B/A/S before·after·split.
          </p>
        </div>

        <SmartEditPanel
          videoId={video.id}
          payload={history.payload}
          currentTime={player.currentTime}
          onPayloadChange={(next) => history.patch(next)}
          onAddItems={(items: RectItem[]) => {
            for (const item of items) history.addItem(item);
          }}
        />

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

        <ProcessPanel
          videoId={video.id}
          payload={history.payload}
          activeMaskId={activeMaskId}
        />
      </main>
    </div>
  );
}
