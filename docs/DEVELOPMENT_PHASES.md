# Development phases — Private AI Video Cleaner

This document is the source of truth for how the product is built. **Only the current phase is implemented until you approve the next.**

---

## Phase 1 — Repository & project configuration ✅

GitHub-ready monorepo with Next.js + FastAPI scaffolds.

---

## Phase 2 — Auth, uploads, metadata & progress ✅

Owner authentication, secure chunked uploads, metadata, progress APIs.

---

## Phase 3 — Mobile-first video editor *(current)*

**Goal:** CapCut/VN-style selection editor for marking regions — no AI removal, no FFmpeg processing.

**Deliverables:**
- Dedicated upload page
- Video preview player with play/pause, seek, frame step, zoom
- Timeline with playhead + selection markers
- Rectangle + brush tools, undo/redo, clear, mask preview
- Touch gestures (pinch zoom, large hit targets) for iPhone
- Save / load selection masks via API
- Premium dark responsive UI with smooth motion

**Out of scope:** AI inpainting, FFmpeg clean/export pipeline.

---

## Phase 4 — Processing pipeline & MP4 export

Apply cleaning via OpenCV/FFmpeg and export processed MP4.

---

## Phase 5 — Optional logo / text overlay

Brand the exported video after editing.

---

## Phase 6 — AI-assisted inpainting architecture

Plug generative inpainting behind a processing strategy interface.

---

## Phase 7 — Hardening & production

CI depth, object storage adapter, observability, private deploy.

---

## Approval gate

After each phase lands, **wait for explicit approval** before starting the next phase.
