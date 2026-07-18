/**
 * Frontend API configuration.
 * Empty base URL uses same-origin Next.js rewrites to the FastAPI backend.
 */
export const apiConfig = {
  baseUrl: (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, ""),
} as const;
