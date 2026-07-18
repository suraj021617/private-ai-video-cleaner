# Processing engine + LaMa AI (Phase 5)

## Pipeline (unchanged shell)

```
Upload → Mask Editor → Mask Saved → Processing Engine → Export
```

Only the `ai_inpaint` strategy is new/real. Classic strategies remain.

## LaMa plugin

Path: `backend/app/processing/plugins/lama/`  
(Symlink: `backend/processing/plugins/lama`)

| File | Role |
|------|------|
| `download.py` | Resumable checkpoint download |
| `model_manager.py` | Load JIT model, CUDA/CPU, OOM → CPU |
| `utils.py` | Crop/pad, feather, color match, blend |
| `predict.py` | Crop-only LaMa inference + hard outside copy |

Checkpoint: `models/lama/big-lama.pt` (auto-download on first AI run).

## Invariants

1. Only the padded bbox around the mask is sent to LaMa (default pad 64px).
2. Soft feather blending + color correction.
3. Final hard copy: `result[mask==0] = original[mask==0]`.
4. FPS / resolution / audio preserved via existing FFmpeg muxer.
5. Export `mp4` or `mov`.

## Settings API

- `GET/PUT /api/v1/settings`
- `GET /api/v1/settings/lama-status`
- `POST /api/v1/settings/lama-ensure`

## Jobs

`strategy: "ai_inpaint"` is accepted. Progress includes `fps`, `eta_seconds`, `model_loaded`.
