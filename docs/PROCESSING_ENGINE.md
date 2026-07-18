# Processing engine architecture (Phase 4)

## Goal

Production-ready mask-scoped video processing with FFmpeg + OpenCV, GPU when
available, CPU fallback, and a plugin interface for future AI inpainting.

## Pipeline

```
source MP4
  → FrameReader (OpenCV decode, source fps/resolution)
  → per-frame mask raster (rect/brush, time-aware)
  → ProcessingPlugin.process_frame (blur | fill | classic_inpaint)
  → FrameWriter (temp video)
  → ffmpeg mux (libx264 + original audio stream copy)
  → storage/processed/{user_id}/{job_id}.mp4
```

## Invariants

1. Output fps equals source fps used by the reader.
2. Output width/height equal source frame size.
3. Original audio is stream-copied when present (`-c:a copy`).
4. Plugins must composite so pixels where `mask == 0` are unchanged.
5. `ai_inpaint` is registered but unavailable (HTTP 501).

## Device selection

`detect_compute_device()` chooses:

1. CUDA (`cv2.cuda`) when devices > 0
2. OpenCL (`cv2.UMat`) when enabled
3. CPU otherwise

Blur uses GPU paths when present; classic inpaint uses CPU OpenCV.

## Plugin API

```python
class ProcessingPlugin(ABC):
    name: ProcessingStrategy
    available: bool
    def process_frame(self, ctx: FrameContext, options: StrategyOptions) -> ProcessFrameResult: ...
```

Future AI models implement the same interface and register in
`app.processing.strategies`.

## Jobs API

- `GET /api/v1/processing/capabilities`
- `POST /api/v1/videos/{id}/jobs`
- `GET /api/v1/jobs/{id}`
- `GET /api/v1/jobs/{id}/progress`
- `GET /api/v1/jobs/{id}/download`

## Benchmarks

```bash
cd backend
pytest -q -m benchmark -s
```
