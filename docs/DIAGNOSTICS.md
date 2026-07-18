# Production Diagnostics (Phase 8)

Additive module to verify the app is healthy before processing videos.

## UI

Open **`/diagnostics`** (linked from Library, Settings, Editor).

Dark dashboard with green / yellow / red status.

## API (all authenticated)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/diagnostics/summary` | Fast system + models snapshot |
| GET | `/api/v1/diagnostics/system` | FFmpeg, CUDA, RAM, disk, OS, … |
| GET | `/api/v1/diagnostics/models` | LaMa / ProPainter / STTN / classic |
| POST | `/api/v1/diagnostics/models/refresh` | Ensure/download LaMa, re-check |
| POST | `/api/v1/diagnostics/benchmark` | FPS / memory / microbench + chart data |
| POST | `/api/v1/diagnostics/video-test` | Sample video × Blur/Fill/Classic/LaMa |
| POST | `/api/v1/diagnostics/export-test` | MP4/MOV/MKV × H264/HEVC checks |
| GET | `/api/v1/diagnostics/report` | JSON health report |
| GET | `/api/v1/diagnostics/report.txt` | Download TXT |
| GET | `/api/v1/diagnostics/report.json` | Download JSON |
| GET | `/api/v1/diagnostics/logs` | Ring-buffer log viewer |
| DELETE | `/api/v1/diagnostics/logs` | Clear buffer |
| GET | `/api/v1/diagnostics/logs/export` | Download logs |
| POST | `/api/v1/diagnostics/error-help` | Reason + suggested fix |

## Compatibility

- No database migrations
- Existing endpoints unchanged (optional fields only on job progress)
- Existing features preserved
