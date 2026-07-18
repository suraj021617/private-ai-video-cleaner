# Development phases — Private AI Video Cleaner

**Only the current phase is implemented until you approve the next.**

---

## Phase 1 — Repository & project configuration ✅
## Phase 2 — Auth, uploads, metadata & progress ✅
## Phase 3 — Mobile-first video editor ✅
## Phase 4 — Processing engine ✅

## Phase 5 — Real AI video inpainting (LaMa) *(current)*

**Goal:** Replace placeholder AI with production LaMa inpainting.

**Deliverables:**
- LaMa plugin (`download`, `model_manager`, `predict`, `utils`)
- Crop-only inference + feather blend + color correction
- GPU auto-detect with CPU / OOM fallback
- Resumable model download to `models/lama/`
- Process panel: Classic / Blur / Fill / AI Inpaint + GPU/CPU/model/ETA/FPS
- Settings page for model path, GPU, threads, padding, blend, temp dir
- Export MP4 / MOV
- Unit + integration tests (existing Phase 4 tests still pass)

---

## Phase 6 — Optional logo / text overlay
## Phase 7 — Hardening & production

---

## Approval gate

Wait for explicit approval before the next phase.
