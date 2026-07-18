"use client";

import type { EditorTool } from "@/lib/editor/types";

type Props = {
  tool: EditorTool;
  brushSize: number;
  showMask: boolean;
  canUndo: boolean;
  canRedo: boolean;
  onToolChange: (tool: EditorTool) => void;
  onBrushSizeChange: (size: number) => void;
  onToggleMask: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onClear: () => void;
};

const tools: { id: EditorTool; label: string }[] = [
  { id: "rect", label: "Rect" },
  { id: "brush", label: "Brush" },
  { id: "pan", label: "Pan" },
];

export function EditorToolbar({
  tool,
  brushSize,
  showMask,
  canUndo,
  canRedo,
  onToolChange,
  onBrushSizeChange,
  onToggleMask,
  onUndo,
  onRedo,
  onClear,
}: Props) {
  return (
    <div className="space-y-3 rounded-2xl border border-border bg-surface/90 p-3 backdrop-blur">
      <div className="grid grid-cols-3 gap-2">
        {tools.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onToolChange(item.id)}
            className={`h-11 rounded-xl text-sm font-semibold transition active:scale-95 ${
              tool === item.id
                ? "bg-accent text-[#041614]"
                : "border border-border bg-surface-elevated text-foreground"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tool === "brush" ? (
        <label className="block">
          <div className="mb-2 flex items-center justify-between text-xs text-muted">
            <span>Brush size</span>
            <span className="font-[family-name:var(--font-mono)]">
              {Math.round(brushSize * 100)}
            </span>
          </div>
          <input
            type="range"
            min={0.01}
            max={0.12}
            step={0.005}
            value={brushSize}
            onChange={(e) => onBrushSizeChange(Number(e.target.value))}
            className="w-full accent-[var(--accent)]"
          />
        </label>
      ) : null}

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <button
          type="button"
          onClick={onUndo}
          disabled={!canUndo}
          className="h-11 rounded-xl border border-border text-sm disabled:opacity-40"
        >
          Undo
        </button>
        <button
          type="button"
          onClick={onRedo}
          disabled={!canRedo}
          className="h-11 rounded-xl border border-border text-sm disabled:opacity-40"
        >
          Redo
        </button>
        <button
          type="button"
          onClick={onClear}
          className="h-11 rounded-xl border border-border text-sm text-danger"
        >
          Clear
        </button>
        <button
          type="button"
          onClick={onToggleMask}
          className={`h-11 rounded-xl text-sm font-semibold ${
            showMask
              ? "bg-accent-soft text-accent"
              : "border border-border text-foreground"
          }`}
        >
          Mask {showMask ? "On" : "Off"}
        </button>
      </div>
    </div>
  );
}
