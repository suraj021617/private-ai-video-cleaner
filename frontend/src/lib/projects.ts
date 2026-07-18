import { apiRequest } from "@/lib/api";
import type { SelectionPayload } from "@/lib/editor/types";

export type ProjectSummary = {
  id: string;
  name: string;
  video_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectDetail = ProjectSummary & {
  payload: {
    version?: number;
    video_id?: string | null;
    masks?: unknown[];
    timeline?: { zoom?: number; current_time?: number };
    settings?: Record<string, unknown>;
    ai_selections?: unknown[];
    undo_stack?: SelectionPayload[];
    redo_stack?: SelectionPayload[];
    selection?: SelectionPayload;
  };
};

export async function listProjects(): Promise<{
  items: ProjectSummary[];
  total: number;
}> {
  return apiRequest("/api/v1/projects", { method: "GET" });
}

export async function createProject(input: {
  name: string;
  video_id: string;
  payload: ProjectDetail["payload"];
}): Promise<ProjectDetail> {
  return apiRequest("/api/v1/projects", { json: input });
}

export async function updateProject(
  projectId: string,
  input: {
    name?: string;
    payload?: ProjectDetail["payload"];
  },
): Promise<ProjectDetail> {
  return apiRequest(`/api/v1/projects/${projectId}`, {
    method: "PUT",
    json: input,
  });
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  return apiRequest(`/api/v1/projects/${projectId}`, { method: "GET" });
}
