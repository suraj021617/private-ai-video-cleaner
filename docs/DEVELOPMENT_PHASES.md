# Development phases — Private AI Video Cleaner

This document is the source of truth for how the product is built. **Only the current phase is implemented until you approve the next.**

---

## Phase 1 — Repository & project configuration *(current)*

**Goal:** GitHub-ready monorepo with configured Next.js and FastAPI apps, empty scalable folders, and documented roadmap.

**Deliverables:**
- Root README, `.gitignore`, env examples
- `frontend/` — Next.js + TypeScript + Tailwind (premium dark shell)
- `backend/` — FastAPI app package layout, deps for future OpenCV/FFmpeg work
- `docs/`, `shared/`, `storage/`, `scripts/`, CI workflow stub
- Architecture notes for auth, media, and AI inpainting extension points

**Out of scope:** Auth, uploads, editor tools, processing jobs.

---

## Phase 2 — Local developer experience & API contract

**Goal:** Reliable local run story and a thin, versioned API surface.

**Deliverables:**
- Health/readiness endpoints with structured responses
- Shared CORS + env validation
- Optional Docker Compose for API + frontend
- OpenAPI tags aligned with future domains (`auth`, `videos`, `jobs`, `exports`)

---

## Phase 3 — Secure authentication

**Goal:** Private app access for the owner only.

**Deliverables:**
- Registration/login (or invite-only single-owner bootstrap)
- HttpOnly secure cookies / session tokens
- Protected API routes & Next.js middleware guards
- Password hashing (argon2/bcrypt), rate limiting on auth endpoints
- CSRF strategy for cookie-based sessions

---

## Phase 4 — Video upload & storage

**Goal:** Accept owner videos safely and persist them for editing.

**Deliverables:**
- Multipart upload with size/type validation (MP4, MOV, etc.)
- Per-user storage isolation under `storage/uploads`
- Metadata records (duration, resolution, codec via FFmpeg probe)
- Signed/temporary access URLs for preview

---

## Phase 5 — Video preview

**Goal:** Mobile-first dark UI player for reviewing source footage.

**Deliverables:**
- Responsive video preview component
- Frame scrubbing / timestamp display
- Loading and error states
- Sync preview with selection timeline (prep for Phase 6)

---

## Phase 6 — Manual rectangle & brush selection

**Goal:** Let the owner mark regions to clean across frames/time.

**Deliverables:**
- Canvas overlay on the video preview
- Rectangle tool (drag to select)
- Brush/mask tool with adjustable size
- Selection model: shapes + raster mask + time range
- Persist selections to the API

---

## Phase 7 — Processing pipeline & MP4 export

**Goal:** Apply cleaning and export a processed MP4.

**Deliverables:**
- Async job system (status polling / websocket later)
- OpenCV mask application + FFmpeg encode pipeline
- Classic inpaint / blur / fill strategies as baseline
- Downloadable export under `storage/processed`

---

## Phase 8 — Optional logo / text overlay

**Goal:** Brand the exported video after editing.

**Deliverables:**
- Overlay config (image or text, position, opacity, duration)
- FFmpeg overlay filter integration
- Preview of overlay before final export

---

## Phase 9 — AI-assisted inpainting architecture

**Goal:** Plug in generative / AI inpainting without rewriting the pipeline.

**Deliverables:**
- `ProcessingStrategy` interface (classic vs AI)
- Model worker stub (GPU optional)
- Mask → model → frame compose contract
- Feature flag to enable AI path per job

---

## Phase 10 — Hardening & production

**Goal:** Ship privately with confidence.

**Deliverables:**
- CI (lint, typecheck, unit tests)
- Object storage adapter (S3-compatible) for media
- Observability, backups, secrets management
- Production Docker images & reverse proxy TLS

---

## Approval gate

After each phase lands, **wait for explicit approval** before starting the next phase.
