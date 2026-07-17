/**
 * Frontend API configuration.
 * Auth-aware clients land in Phase 3+.
 */
export const apiConfig = {
  baseUrl:
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
    "http://localhost:8000",
} as const;
