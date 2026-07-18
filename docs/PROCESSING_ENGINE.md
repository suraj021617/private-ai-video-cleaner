# Processing engine

## Pipeline

```
decode frames → rasterize mask (keyframes + polish) → strategy plugin → encode → mux audio
```

Guarantees:

- Source FPS preserved (`-r` on encode)
- Resolution preserved unless explicit 4K/export size requested
- Audio stream-copied (`-c:a copy`) when present
- Color / HDR metadata copied best-effort
- Pixels outside the mask are never modified

## Strategies

| Name | Plugin | Notes |
|------|--------|-------|
| `blur` | OpenCV Gaussian | Always available |
| `fill` | Solid fill | Always available |
| `classic_inpaint` | OpenCV Telea/NS | Always available |
| `ai_inpaint` | LaMa | Torch; GPU→CPU; OOM retry |
| `propainter` | Slot | Falls back → LaMa → classic |
| `sttn` | Slot | Falls back → LaMa → classic |

Fallback resolution: `resolve_strategy()` in `app/processing/strategies/__init__.py`.

## Mask payload

v1 `items` remain supported. Optional Phase 6 fields:

- `keyframes` on rect items (interpolated per frame)
- `masks[]` named groups
- `feather`, `expansion`, `edge_refine`

## Export

Containers: `mp4`, `mov`, `mkv`  
Codecs: `h264`, `hevc` (HEVC→H264 retry if encoder missing)  
Quality: `fast` / `balanced` / `best` (CRF + preset)  
Optional `export_width` / `export_height` (e.g. 3840×2160)

## Devices

Detection order: CUDA → OpenCL → CPU.  
Capabilities endpoint exposes benchmark micro-timings and memory snapshot.
