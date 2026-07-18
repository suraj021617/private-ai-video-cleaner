import { apiRequest, rememberCsrfToken } from "./api";

export type User = {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
};

export type AuthResponse = {
  user: User;
  csrf_token: string;
};

export type AuthStatus = {
  bootstrap_required: boolean;
  authenticated: boolean;
};

export async function fetchAuthStatus(): Promise<AuthStatus> {
  return apiRequest<AuthStatus>("/api/v1/auth/status", { method: "GET" });
}

export async function fetchMe(): Promise<AuthResponse> {
  const result = await apiRequest<AuthResponse>("/api/v1/auth/me", {
    method: "GET",
  });
  rememberCsrfToken(result.csrf_token);
  return result;
}

export async function bootstrapOwner(input: {
  email: string;
  password: string;
  display_name: string;
}): Promise<AuthResponse> {
  const result = await apiRequest<AuthResponse>("/api/v1/auth/bootstrap", {
    json: input,
  });
  rememberCsrfToken(result.csrf_token);
  return result;
}

export async function login(input: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  const result = await apiRequest<AuthResponse>("/api/v1/auth/login", {
    json: input,
  });
  rememberCsrfToken(result.csrf_token);
  return result;
}

export async function logout(): Promise<void> {
  await apiRequest<void>("/api/v1/auth/logout", { method: "POST" });
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem("pavc_csrf");
  }
}
