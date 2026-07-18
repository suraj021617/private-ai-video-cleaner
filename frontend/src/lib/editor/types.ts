/** Editor selection document types (normalized 0–1 coordinates). */

export type Point = {
  x: number;
  y: number;
};

export type Keyframe = {
  time: number;
  x: number;
  y: number;
  w: number;
  h: number;
};

export type RectItem = {
  id: string;
  type: "rect";
  x: number;
  y: number;
  w: number;
  h: number;
  start_time: number;
  end_time: number;
  enabled?: boolean;
  label?: string | null;
  keyframes?: Keyframe[];
};

export type BrushItem = {
  id: string;
  type: "brush";
  points: Point[];
  size: number;
  start_time: number;
  end_time: number;
  enabled?: boolean;
  label?: string | null;
};

export type SelectionItem = RectItem | BrushItem;

export type MaskGroup = {
  id: string;
  name: string;
  enabled: boolean;
  items: SelectionItem[];
};

export type SelectionPayload = {
  version: 1 | 2;
  video_width: number;
  video_height: number;
  fps: number | null;
  items: SelectionItem[];
  masks?: MaskGroup[];
  feather?: number;
  expansion?: number;
  edge_refine?: number;
};

export type EditorTool = "rect" | "brush" | "pan";

export type MaskSummary = {
  id: string;
  video_id: string;
  name: string;
  created_at: string;
  updated_at: string;
  item_count: number;
};

export type MaskDetail = MaskSummary & {
  payload: SelectionPayload;
};

export function createEmptyPayload(
  width: number,
  height: number,
  fps: number | null,
): SelectionPayload {
  return {
    version: 1,
    video_width: width,
    video_height: height,
    fps,
    items: [],
    masks: [],
    feather: 0,
    expansion: 0,
    edge_refine: 0,
  };
}

export function newId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}
