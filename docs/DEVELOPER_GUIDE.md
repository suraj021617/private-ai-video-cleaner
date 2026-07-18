# Developer guide

## Architecture overview

- **Frontend** (`frontend/`): Next.js App Router editor, library, settings
- **Backend** (`backend/app/`): FastAPI, SQLAlchemy, Argon2 sessions
- **Processing** (`backend/app/processing/`): decode → mask raster → strategy plugin → encode/mux
- **Plugins** (`backend/app/processing/plugins/`): LaMa (real), ProPainter/STTN (slots)
- **Smart edit** (`backend/app/services/smart_edit.py`): detect, track, refine, thumbnails
- **Projects** (`backend/app/models/project.py` + API): save/restore editor state

## Adding a processing strategy

1. Add enum value in `app/processing/types.py` and `app/schemas/enums.py`
2. Implement `ProcessingPlugin` under `strategies/` or `plugins/`
3. Register in `strategies/__init__.py` and optionally add a fallback chain entry
4. Extend `JobCreateRequest.strategy` Literal
5. Add UI option in `ProcessPanel.tsx`
6. Add tests proving outside-mask pixels are unchanged

## Smart editing extension points

- `detect_objects_in_frame` — swap saliency for a local detector
- `track_box_across_frames` — CSRT/KCF today; keyframes feed rasterizer
- Payload fields: `feather`, `expansion`, `edge_refine`, `keyframes`, `masks[]`

## Job control

Statuses: `queued` → `running` → `completed` | `failed` | `cancelled` (also `paused`).

APIs: `POST /jobs/{id}/pause|resume|cancel`. Startup recovery re-queues crashed `running` jobs.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Stress / bench: `tests/benchmarks/test_pipeline_bench.py`.

## Phase backups

Before Phase 6 edits, files were copied to `*.phase6.bak`. Do not commit backups.
