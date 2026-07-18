# Development phases — Private AI Video Cleaner

This document is the source of truth for how the product is built. **Only the current phase is implemented until you approve the next.**

---

## Phase 1 — Repository & project configuration ✅

## Phase 2 — Auth, uploads, metadata & progress ✅

## Phase 3 — Mobile-first video editor ✅

## Phase 4 — Processing engine *(current)*

**Goal:** Production FFmpeg + OpenCV pipeline that processes only inside user masks.

**Deliverables:**
- Modular plugin pipeline (`blur`, `fill`, `classic_inpaint`)
- Frame-by-frame decode/encode preserving fps, resolution, audio
- GPU acceleration when available + CPU fallback
- Jobs API with progress + MP4 download
- Benchmark tests
- Future AI plugin slot (`ai_inpaint` registered, unavailable)

**Out of scope:** AI removal models, logo/text overlays.

See `docs/PROCESSING_ENGINE.md`.

---

## Phase 5 — Optional logo / text overlay

## Phase 6 — AI-assisted inpainting

## Phase 7 — Hardening & production

---

## Approval gate

After each phase lands, **wait for explicit approval** before starting the next phase.
