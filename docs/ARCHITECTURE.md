# Architecture — Private AI Video Cleaner

## Principles

1. **Private by default** — only authenticated owners can upload, edit, or export.
2. **Permission boundary** — the product assumes the user has rights to edit the media; UI and docs reinforce that.
3. **Separation of concerns** — UI (Next.js), API (FastAPI), media workers (FFmpeg/OpenCV), future AI workers.
4. **Job-oriented processing** — long video work never blocks HTTP request threads.
5. **Strategy pattern for cleaning** — classic OpenCV/FFmpeg paths today; AI inpainting later behind the same interface.

## High-level components

```
┌─────────────────────────────────────────────────────────┐
│  frontend (Next.js)                                     │
│  pages: auth | library | editor | export                │
│  editor: preview + canvas (rect/brush) + overlay UI     │
└───────────────────────────┬─────────────────────────────┘
                            │ REST / future WS
┌───────────────────────────▼─────────────────────────────┐
│  backend (FastAPI)                                      │
│  routers: auth | videos | selections | jobs | exports   │
│  services: storage | probe | process | overlay          │
│  workers: ffmpeg_worker | opencv_worker | ai_worker*    │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  storage/                                               │
│  uploads/ | processed/ | temp/                          │
│  (later: S3-compatible object store)                    │
└─────────────────────────────────────────────────────────┘
```

\* `ai_worker` is a Phase 9 extension point only.

## Frontend structure (target)

```
frontend/
  src/
    app/                 # App Router routes
    components/
      ui/                # Primitives
      editor/            # Preview, canvas tools, overlays
      auth/
    lib/                 # API client, auth helpers, config
    styles/              # Global + design tokens
    types/
```

## Backend structure (target)

```
backend/
  app/
    main.py              # FastAPI entry
    core/                # settings, security, logging
    api/                 # versioned routers
    models/              # DB / domain models
    schemas/             # Pydantic request/response
    services/            # Business logic
    workers/             # Media & AI jobs
    db/                  # Session / migrations (later)
```

## Media pipeline (Phases 7–9)

1. Client submits selection mask + time range + strategy.
2. API creates a `Job` (`queued` → `running` → `completed` | `failed`).
3. Worker loads source video, applies mask per frame (or keyframe range).
4. Strategy:
   - `classic_inpaint` / `blur` / `fill` (OpenCV + FFmpeg)
   - `ai_inpaint` (future model worker)
5. Optional overlay pass.
6. Encode H.264 MP4 → `storage/processed/{job_id}.mp4`.
7. Client downloads via authenticated export endpoint.

## Security sketch (Phase 3+)

- Argon2/bcrypt password hashing
- HttpOnly, Secure, SameSite cookies
- Auth middleware on all media routes
- Upload MIME/extension allowlist + max size
- Path traversal protection on storage keys
- Rate limits on auth and upload

## Scalability path

| Stage | Approach |
|-------|----------|
| Local / single owner | Filesystem storage + in-process background tasks |
| Small private deploy | Redis queue + dedicated worker process |
| Growth | Object storage + horizontal API + GPU AI workers |

## Design system (UI)

- Mobile-first layouts
- Premium dark theme (near-black surfaces, restrained accent — not generic purple glow)
- Expressive typography via Next.js font loading
- Editor canvas as the primary interaction surface after auth
