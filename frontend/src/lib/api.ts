/**
 * Browser API client for the FastAPI backend.
 * Uses cookie sessions + CSRF header on unsafe methods.
 */

import { apiConfig } from "./config";

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};

export class ApiError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.status = status;
    this.code = body.error.code;
    this.details = body.error.details ?? {};
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : null;
}

export function rememberCsrfToken(token: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem("pavc_csrf", token);
}

export function getCsrfToken(): string | null {
  if (typeof window !== "undefined") {
    const stored = window.sessionStorage.getItem("pavc_csrf");
    if (stored) return stored;
  }
  return readCookie("pavc_csrf");
}

type RequestOptions = {
  method?: string;
  body?: BodyInit | null;
  json?: unknown;
  headers?: Record<string, string>;
  csrf?: boolean;
};

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers ?? {}),
  };

  let body = options.body ?? null;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  }

  const method = options.method ?? (options.json !== undefined ? "POST" : "GET");
  const needsCsrf =
    options.csrf !== false && !["GET", "HEAD", "OPTIONS"].includes(method);
  if (needsCsrf) {
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  const response = await fetch(`${apiConfig.baseUrl}${path}`, {
    method,
    headers,
    body,
    credentials: "include",
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    if (payload?.error) {
      throw new ApiError(response.status, payload as ApiErrorBody);
    }
    throw new ApiError(response.status, {
      error: {
        code: "request_failed",
        message: response.statusText || "Request failed",
      },
    });
  }

  return payload as T;
}
