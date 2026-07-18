import { apiRequest, getCsrfToken } from "./api";
import { apiConfig } from "./config";

export type VideoMetadata = {
  duration_seconds: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  container: string | null;
  bitrate: number | null;
};

export type Video = {
  id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: string;
  created_at: string;
  updated_at: string;
  metadata: VideoMetadata;
};

export type UploadProgress = {
  id: string;
  status: string;
  bytes_received: number;
  bytes_total: number;
  chunks_received: number;
  chunks_total: number;
  percent: number;
  video_id: string | null;
  error: string | null;
};

export type UploadInit = {
  id: string;
  chunk_size: number;
  chunks_total: number;
  status: string;
};

export async function listVideos(): Promise<{ items: Video[]; total: number }> {
  return apiRequest("/api/v1/videos", { method: "GET" });
}

export async function getVideo(videoId: string): Promise<Video> {
  return apiRequest(`/api/v1/videos/${videoId}`, { method: "GET" });
}

export async function deleteVideo(videoId: string): Promise<void> {
  await apiRequest<void>(`/api/v1/videos/${videoId}`, { method: "DELETE" });
}

export function videoContentUrl(videoId: string): string {
  return `${apiConfig.baseUrl}/api/v1/videos/${videoId}/content`;
}

export async function uploadVideo(
  file: File,
  onProgress?: (progress: UploadProgress) => void,
): Promise<Video> {
  const init = await apiRequest<UploadInit>("/api/v1/uploads", {
    json: {
      filename: file.name,
      size_bytes: file.size,
      content_type: file.type || "application/octet-stream",
    },
  });

  const csrf = getCsrfToken();
  for (let index = 0; index < init.chunks_total; index += 1) {
    const start = index * init.chunk_size;
    const end = Math.min(start + init.chunk_size, file.size);
    const chunk = file.slice(start, end);

    const response = await fetch(
      `${apiConfig.baseUrl}/api/v1/uploads/${init.id}/chunks/${index}`,
      {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/octet-stream",
          ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        },
        body: chunk,
      },
    );

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.error?.message ?? "Chunk upload failed");
    }
    onProgress?.(payload as UploadProgress);
  }

  const video = await apiRequest<Video>(`/api/v1/uploads/${init.id}/complete`, {
    method: "POST",
  });
  return video;
}
