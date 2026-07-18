import { apiRequest } from "@/lib/api";
import { apiConfig } from "@/lib/config";
import type { SelectionPayload } from "@/lib/editor/types";

export type ProcessingStrategyName =
  | "blur"
  | "fill"
  | "classic_inpaint"
  | "ai_inpaint"
  | "propainter"
  | "sttn";

export type ExportFormat = "mp4" | "mov" | "mkv";
export type ExportCodec = "h264" | "hevc";
export type ExportQuality = "fast" | "balanced" | "best";

export type Job = {
  id: string;
  video_id: string;
  mask_id: string | null;
  strategy: string;
  strategy_used?: string | null;
  status: string;
  prefer_gpu: boolean;
  device_used: string | null;
  frames_total: number;
  frames_done: number;
  percent: number;
  message: string | null;
  error_message: string | null;
  download_ready: boolean;
  export_format?: string;
  export_codec?: string;
  export_quality?: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  queue_position?: number | null;
};

export type JobProgress = {
  id: string;
  status: string;
  frames_total: number;
  frames_done: number;
  percent: number;
  message: string | null;
  device_used: string | null;
  error: string | null;
  fps?: number | null;
  eta_seconds?: number | null;
  model_loaded?: boolean | null;
  strategy_used?: string | null;
  fallback_from?: string | null;
  queue_position?: number | null;
};

export async function createProcessingJob(
  videoId: string,
  input: {
    strategy: ProcessingStrategyName;
    mask_id?: string | null;
    payload?: SelectionPayload;
    prefer_gpu?: boolean;
    export_format?: ExportFormat;
    export_codec?: ExportCodec;
    export_quality?: ExportQuality;
    export_width?: number | null;
    export_height?: number | null;
    padding?: number;
    blend_strength?: number;
    feather_radius?: number;
    mask_expansion?: number;
    edge_refine?: number;
  },
): Promise<Job> {
  return apiRequest(`/api/v1/videos/${videoId}/jobs`, {
    json: {
      strategy: input.strategy,
      mask_id: input.mask_id ?? null,
      payload: input.payload,
      prefer_gpu: input.prefer_gpu ?? true,
      export_format: input.export_format ?? "mp4",
      export_codec: input.export_codec ?? "h264",
      export_quality: input.export_quality ?? "balanced",
      export_width: input.export_width ?? undefined,
      export_height: input.export_height ?? undefined,
      padding: input.padding,
      blend_strength: input.blend_strength,
      feather_radius: input.feather_radius,
      mask_expansion: input.mask_expansion,
      edge_refine: input.edge_refine,
    },
  });
}

export async function getJobProgress(jobId: string): Promise<JobProgress> {
  return apiRequest(`/api/v1/jobs/${jobId}/progress`, { method: "GET" });
}

export async function pauseJob(jobId: string): Promise<Job> {
  return apiRequest(`/api/v1/jobs/${jobId}/pause`, { method: "POST" });
}

export async function resumeJob(jobId: string): Promise<Job> {
  return apiRequest(`/api/v1/jobs/${jobId}/resume`, { method: "POST" });
}

export async function cancelJob(jobId: string): Promise<Job> {
  return apiRequest(`/api/v1/jobs/${jobId}/cancel`, { method: "POST" });
}

export function jobDownloadUrl(jobId: string): string {
  return `${apiConfig.baseUrl}/api/v1/jobs/${jobId}/download`;
}
