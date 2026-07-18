/** Editor selection document types (normalized 0–1 coordinates). */

export type Point = {
  x: number;
  y: number;
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
};

export type BrushItem = {
  id: string;
  type: "brush";
  points: Point[];
  size: number;
  start_time: number;
  end_time: number;
};

export type SelectionItem = RectItem | BrushItem;

export type SelectionPayload = {
  version: 1;
  video_width: number;
  video_height: number;
  fps: number | null;
  items: SelectionItem[];
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
  };
}

export function newId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}
