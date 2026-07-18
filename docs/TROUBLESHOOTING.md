# Troubleshooting

## FFmpeg / ffprobe not found

Install FFmpeg and ensure both `ffmpeg` and `ffprobe` are on `PATH`. `/api/v1/ready` reports `ffmpeg_available`.

## AI Inpaint fails with torch missing

Install PyTorch matching your platform (`requirements.txt` pins a CPU/CUDA-capable wheel set). Without torch, choose Classic / Blur / Fill.

## CUDA out of memory

The pipeline retries the frame on CPU after OOM. Reduce resolution, close other GPU apps, or set `lama_prefer_gpu=false` in Settings.

## ProPainter / STTN unavailable

These are optional plugin slots. If packages/models are missing, the job runner falls back to LaMa, then classic inpaint. Capabilities API lists `available` and `fallback` per strategy.

## Job stuck in running after crash

On API startup, interrupted `running` jobs are re-queued automatically (`recover_interrupted_jobs`).

## Export HEVC fails

Encoder falls back to H.264 when `libx265` is unavailable. Install a full FFmpeg build with HEVC support for HEVC exports.

## Mask not applied / outside pixels changed

Outside-mask pixels must remain unchanged. If a plugin violates this, report a regression — unit tests assert the invariant.

## CSRF / 403 on mutating requests

Send `X-CSRF-Token` from the `pavc_csrf` cookie on POST/PUT/DELETE. The Next.js app handles this via `apiRequest`.

## Large video memory pressure

Prefer Fast/Balanced quality, process shorter ranges, and monitor `/api/v1/processing/capabilities` → `memory`.
