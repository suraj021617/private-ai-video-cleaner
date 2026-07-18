# Development phases — Private AI Video Cleaner

This document is the source of truth for how the product is built. **Only the current phase is implemented until you approve the next.**

---

## Phase 1 — Repository & project configuration ✅

**Goal:** GitHub-ready monorepo with configured Next.js and FastAPI apps.

**Deliverables:** Root docs, frontend/backend scaffolds, storage folders, CI stub.

---

## Phase 2 — Auth, uploads, metadata & progress *(current)*

**Goal:** Production-ready private authentication and secure video upload system.

**Deliverables:**
- Complete API contract (`docs/API_CONTRACT.md`)
- Owner bootstrap + login + logout + session cookies + CSRF
- Password hashing (Argon2), rate limiting, structured errors
- Chunked upload APIs with progress endpoint
- Per-user storage layout
- Video list/detail/metadata/content/delete
- ffprobe metadata extraction (no encode/clean pipeline)
- Frontend login, bootstrap, library + uploader

**Out of scope:** AI inpainting, FFmpeg processing/export, selection editor.

---

## Phase 3 — Video preview polish

**Goal:** Rich mobile-first preview experience on top of authenticated content streaming.

---

## Phase 4 — Manual rectangle & brush selection

**Goal:** Owner marks regions to clean across frames/time.

---

## Phase 5 — Processing pipeline & MP4 export

**Goal:** Apply cleaning via OpenCV/FFmpeg and export processed MP4.

---

## Phase 6 — Optional logo / text overlay

**Goal:** Brand the exported video after editing.

---

## Phase 7 — AI-assisted inpainting architecture

**Goal:** Plug in generative inpainting behind a processing strategy interface.

---

## Phase 8 — Hardening & production

**Goal:** CI depth, object storage adapter, observability, private deploy.

---

## Approval gate

After each phase lands, **wait for explicit approval** before starting the next phase.
