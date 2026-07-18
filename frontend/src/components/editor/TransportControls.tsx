"use client";

type Props = {
  playing: boolean;
  onToggle: () => void;
  onStep: (frames: number) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  zoom: number;
  disabled?: boolean;
};

function IconButton({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="inline-flex h-11 min-w-11 items-center justify-center rounded-xl border border-border bg-surface text-foreground transition active:scale-95 hover:bg-surface-elevated disabled:opacity-40"
    >
      {children}
    </button>
  );
}

export function TransportControls({
  playing,
  onToggle,
  onStep,
  onZoomIn,
  onZoomOut,
  zoom,
  disabled,
}: Props) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-2">
      <IconButton label="Previous frame" onClick={() => onStep(-1)} disabled={disabled}>
        <span className="font-[family-name:var(--font-mono)] text-sm">−1</span>
      </IconButton>
      <button
        type="button"
        aria-label={playing ? "Pause" : "Play"}
        disabled={disabled}
        onClick={onToggle}
        className="inline-flex h-12 min-w-[5.5rem] items-center justify-center rounded-xl bg-accent px-5 text-sm font-semibold text-[#041614] transition active:scale-95 hover:brightness-110 disabled:opacity-40"
      >
        {playing ? "Pause" : "Play"}
      </button>
      <IconButton label="Next frame" onClick={() => onStep(1)} disabled={disabled}>
        <span className="font-[family-name:var(--font-mono)] text-sm">+1</span>
      </IconButton>
      <div className="mx-1 h-8 w-px bg-border" />
      <IconButton label="Zoom out" onClick={onZoomOut} disabled={disabled || zoom <= 1}>
        −
      </IconButton>
      <span className="min-w-14 text-center font-[family-name:var(--font-mono)] text-xs text-muted">
        {Math.round(zoom * 100)}%
      </span>
      <IconButton label="Zoom in" onClick={onZoomIn} disabled={disabled || zoom >= 4}>
        +
      </IconButton>
    </div>
  );
}
