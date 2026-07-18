# Shared contracts (documentation)

Machine-readable OpenAPI remains the source of truth from FastAPI (`/openapi.json`).

This folder holds human-readable notes and optional TypeScript type mirrors once Phase 2 stabilizes the API surface.

## Planned domains

- `auth` — session / user
- `videos` — upload metadata & probe info
- `selections` — rectangles, brush strokes, masks, time ranges
- `jobs` — processing status
- `exports` — downloadable MP4 + overlay options
- `processing` — strategy enum including future `ai_inpaint`
