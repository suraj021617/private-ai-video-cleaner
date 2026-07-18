import { apiRequest } from "@/lib/api";
import type { SelectionItem, SelectionPayload } from "@/lib/editor/types";

export type DetectedObject = {
  id: string;
  label: string;
  score: number;
  x: number;
  y: number;
  w: number;
  h: number;
};

export async function detectObjects(
  videoId: string,
  timeSeconds: number,
): Promise<{ objects: DetectedObject[]; items: SelectionItem[] }> {
  return apiRequest(`/api/v1/videos/${videoId}/smart/detect`, {
    json: { time_seconds: timeSeconds, max_objects: 12 },
  });
}

export async function trackObject(
  videoId: string,
  box: { start_time: number; x: number; y: number; w: number; h: number },
): Promise<{ keyframes: Array<{ time: number; x: number; y: number; w: number; h: number }> }> {
  return apiRequest(`/api/v1/videos/${videoId}/smart/track`, {
    json: { ...box, max_seconds: 8 },
  });
}

export async function fetchTimelineThumbnails(
  videoId: string,
  count = 12,
): Promise<{ thumbnails: Array<{ time: number; data_url: string }> }> {
  return apiRequest(`/api/v1/videos/${videoId}/smart/thumbnails`, {
    json: { count, max_width: 160 },
  });
}

export async function refineMaskPreview(
  videoId: string,
  payload: SelectionPayload,
  timeSeconds: number,
): Promise<{ mask_png_base64: string; width: number; height: number }> {
  return apiRequest(`/api/v1/videos/${videoId}/smart/refine`, {
    json: {
      payload,
      time_seconds: timeSeconds,
      expansion: payload.expansion ?? 0,
      feather: payload.feather ?? 0,
      edge_refine: payload.edge_refine ?? 0,
      width: 320,
      height: 180,
    },
  });
}
