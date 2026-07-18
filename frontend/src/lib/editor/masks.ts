import { apiRequest } from "@/lib/api";
import type { MaskDetail, MaskSummary, SelectionPayload } from "./types";

export async function listMasks(
  videoId: string,
): Promise<{ items: MaskSummary[]; total: number }> {
  return apiRequest(`/api/v1/videos/${videoId}/masks`, { method: "GET" });
}

export async function getMask(
  videoId: string,
  maskId: string,
): Promise<MaskDetail> {
  return apiRequest(`/api/v1/videos/${videoId}/masks/${maskId}`, {
    method: "GET",
  });
}

export async function saveMask(
  videoId: string,
  name: string,
  payload: SelectionPayload,
): Promise<MaskDetail> {
  return apiRequest(`/api/v1/videos/${videoId}/masks`, {
    json: { name, payload },
  });
}

export async function updateMask(
  videoId: string,
  maskId: string,
  input: { name?: string; payload?: SelectionPayload },
): Promise<MaskDetail> {
  return apiRequest(`/api/v1/videos/${videoId}/masks/${maskId}`, {
    method: "PUT",
    json: input,
  });
}

export async function deleteMask(
  videoId: string,
  maskId: string,
): Promise<void> {
  await apiRequest<void>(`/api/v1/videos/${videoId}/masks/${maskId}`, {
    method: "DELETE",
  });
}
