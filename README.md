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

## Quick start

### Prerequisites

- Node.js 20+
- Python 3.11+
- FFmpeg / ffprobe on PATH

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

- App: http://localhost:3000
- API docs: http://localhost:8000/docs

### First run

1. Open http://localhost:3000/bootstrap and create the owner account.
2. Sign in at `/login`.
3. Upload at `/upload`, then open `/editor/{videoId}`.
4. Detect/track masks, choose a strategy, export.

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
