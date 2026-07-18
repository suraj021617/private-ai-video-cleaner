import { apiConfig } from "@/lib/config";
import { apiRequest } from "@/lib/api";
import type { SelectionPayload } from "@/lib/editor/types";

export type ProcessingStrategyName = "blur" | "fill" | "classic_inpaint";

export type Job = {
  id: string;
  video_id: string;
  mask_id: string | null;
  strategy: string;
  status: string;
  prefer_gpu: boolean;
  device_used: string | null;
  frames_total: number;
  frames_done: number;
  percent: number;
  message: string | null;
  error_message: string | null;
  download_ready: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
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
};

export async function createProcessingJob(
  videoId: string,
  input: {
    strategy: ProcessingStrategyName;
    mask_id?: string | null;
    payload?: SelectionPayload;
    prefer_gpu?: boolean;
  },
): Promise<Job> {
  return apiRequest(`/api/v1/videos/${videoId}/jobs`, {
    json: {
      strategy: input.strategy,
      mask_id: input.mask_id ?? null,
      payload: input.payload,
      prefer_gpu: input.prefer_gpu ?? true,
    },
  });
}

export async function getJobProgress(jobId: string): Promise<JobProgress> {
  return apiRequest(`/api/v1/jobs/${jobId}/progress`, { method: "GET" });
}

export function jobDownloadUrl(jobId: string): string {
  return `${apiConfig.baseUrl}/api/v1/jobs/${jobId}/download`;
}
