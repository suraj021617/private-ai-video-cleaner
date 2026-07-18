# Development phases

| Phase | Status | Summary |
|-------|--------|---------|
| 1 Scaffold | Done | Monorepo, health API, dark shell |
| 2 Auth + upload | Done | Bootstrap, sessions, chunked upload, streaming |
| 3 Editor | Done | Timeline, rect/brush masks, undo/redo |
| 4 Processing engine | Done | Blur/fill/classic pipeline, jobs API |
| 5 LaMa AI | Done | Real LaMa crop inpaint, settings, GPU/CPU |
| 6 Smart editing | Done | Detect, track, keyframes, multi-mask polish, thumbs, B/A, undo persistence |
| 7 Advanced AI + production | Done | ProPainter/STTN slots + fallback, export presets, job controls, projects, installer, docs |

## Phase 6–7 acceptance

- [x] Automatic object detection + mask proposals
- [x] Object tracking → keyframes
- [x] Feather / expansion / edge refine
- [x] Before/after + timeline thumbnails
- [x] Undo history persistence (localStorage + project payload)
- [x] Plugin architecture with Classic / Blur / Fill / LaMa / ProPainter / STTN
- [x] Automatic strategy fallback
- [x] MP4/MOV/MKV, H264/HEVC, quality presets, 4K option
- [x] CUDA/OpenCL/CPU + benchmark + memory + OOM retry
- [x] Job queue pause/resume/cancel + recovery
- [x] Project save/restore
- [x] Windows installer / portable scaffolding
- [x] Tests + documentation
