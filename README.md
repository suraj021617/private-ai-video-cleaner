# Private AI Video Cleaner

Private, owner-only desktop/web application for editing videos you have permission to edit — local processing, maximum privacy.

> **Intended use:** Only process media you own or have explicit rights to edit.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (TypeScript), Tailwind CSS |
| Backend | FastAPI (Python), SQLAlchemy, Argon2 sessions |
| Media | FFmpeg / ffprobe, OpenCV |
| AI | LaMa (real), ProPainter/STTN plugin slots |

## Current phase

**Phase 8 — Production diagnostics & stability** (on top of Phase 6–7)

Open `/diagnostics` to verify FFmpeg, GPU, models, run benchmarks, video/export tests, download health reports, and browse logs before processing.

**Phase 6–7 — Smart editing + advanced AI + production hardening**

- Automatic object detection, tracking, keyframes, multi-mask polish (feather / expand / refine)
- Timeline thumbnails, before/after preview, persisted undo, project autosave
- Strategies: Classic, Blur, Fill, LaMa, ProPainter, STTN (automatic fallback)
- Export: MP4 / MOV / MKV, H.264 / HEVC, Fast / Balanced / Best, optional 4K
- Jobs: queue, pause, resume, cancel, crash recovery
- GPU: CUDA → OpenCL → CPU, benchmarks, memory snapshot, OOM retry
- Windows portable package + Inno Setup installer scaffolding

See [docs/](docs/) for architecture, API, installation, troubleshooting, and developer guides.

## Repository layout

```
.
├── frontend/          # Next.js app
├── backend/           # FastAPI API + processing engine
├── desktop/           # Windows portable + installer scripts
├── shared/            # Shared schema notes
├── docs/              # Architecture & guides
├── models/            # Local AI checkpoints (gitignored content)
├── storage/           # Local media (gitignored content)
└── scripts/           # Dev helpers
```

## Quick start (any PC later)

```bash
./scripts/setup-and-run.sh --check   # verify ffmpeg / node / python
./scripts/setup-and-run.sh --lite    # recommended first run (no torch)
# or full AI:
./scripts/setup-and-run.sh
```

Windows: `.\scripts\setup-and-run.ps1 -Lite`

- App: http://127.0.0.1:3000 → `/bootstrap` first
- API docs: http://127.0.0.1:8000/docs

### Building from mobile (no laptop)

You can keep shipping code from your phone via Cursor Cloud + GitHub.
See **[docs/FROM_MOBILE.md](docs/FROM_MOBILE.md)** — that is the “half work” path until you have a PC to run the offline app.

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | HTTP API |
| [docs/PROCESSING_ENGINE.md](docs/PROCESSING_ENGINE.md) | Pipeline & plugins |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | Install & deploy |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Extending the app |
| [desktop/README.md](desktop/README.md) | Windows packaging |

## Security notes

- HttpOnly session cookie + CSRF token on mutating requests
- Argon2 password hashing
- Auth rate limiting
- Upload extension/MIME/size validation
- Per-user storage isolation
- Local-only AI inference (no cloud media upload)

## License

Private / all rights reserved. Not for public redistribution of processed third-party media.
