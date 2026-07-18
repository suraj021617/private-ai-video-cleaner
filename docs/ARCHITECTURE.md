# Architecture — Private AI Video Cleaner

## Principles

1. **Private by default** — only authenticated owners can upload, edit, or export.
2. **Permission boundary** — the product assumes the user has rights to edit the media.
3. **Local AI** — inference runs on-device; media is not sent to cloud APIs.
4. **Job-oriented processing** — long video work never blocks HTTP request threads.
5. **Strategy / plugin pattern** — Classic, Blur, Fill, LaMa, ProPainter, STTN behind one interface with automatic fallback.

## High-level components

```
┌─────────────────────────────────────────────────────────┐
│  frontend (Next.js)                                     │
│  auth | library | editor | settings                     │
│  smart edit · timeline thumbs · B/A · projects          │
└───────────────────────────┬─────────────────────────────┘
                            │ REST (+ cookie session)
┌───────────────────────────▼─────────────────────────────┐
│  backend (FastAPI)                                      │
│  auth | uploads | videos | masks | jobs | settings      │
│  smart_edit | projects                                  │
│  processing: ffmpeg_io · mask_raster · strategies       │
│  plugins: lama · propainter · sttn                      │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│  storage/  uploads | processed | temp | projects        │
│  models/   lama (+ future temporal models)              │
└─────────────────────────────────────────────────────────┘
```

## Processing flow

1. Editor persists selection masks (normalized coords, optional keyframes).
2. Job created → queued → worker thread runs `VideoProcessingPipeline`.
3. Per frame: rasterize mask → plugin → write frame.
4. Finalize: encode (H264/HEVC) + mux original audio + metadata.
5. Progress polled via `/jobs/{id}/progress`; pause/resume/cancel supported.

## Device selection

CUDA → OpenCL → CPU. Capabilities API returns benchmark timings and memory.

## Desktop packaging

`desktop/scripts` builds a portable folder and optional Inno Setup installer with desktop shortcut and auto-update config stub.
