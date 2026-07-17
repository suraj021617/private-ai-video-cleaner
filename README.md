# Private AI Video Cleaner

Private, owner-only web application for editing videos you have permission to edit.

Remove unwanted regions from video frames using manual selection tools, with architecture ready for future AI-assisted inpainting. Export clean MP4 files with optional logo/text overlays.

> **Intended use:** Only process media you own or have explicit rights to edit.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (TypeScript), Tailwind CSS |
| Backend | FastAPI (Python) |
| Media | FFmpeg, OpenCV |
| Auth | Secure session-based auth (Phase 3) |

## Repository layout

```
.
├── frontend/          # Next.js app (UI, auth client, editor)
├── backend/           # FastAPI API, media pipeline, jobs
├── shared/            # Cross-cutting types / schemas (docs)
├── docs/              # Architecture & phase plans
├── storage/           # Local media scratch space (gitignored content)
├── scripts/           # Dev & ops helpers
└── .github/workflows/ # CI placeholders
```

## Development phases

See [docs/DEVELOPMENT_PHASES.md](docs/DEVELOPMENT_PHASES.md) for the full roadmap.

| Phase | Focus |
|-------|--------|
| **1** | Repository init, folders, frontend & backend configuration |
| **2** | Core API health, shared config, local run scripts |
| **3** | Secure authentication |
| **4** | Video upload & storage |
| **5** | Video preview player |
| **6** | Manual rectangle & brush selection |
| **7** | Processing pipeline (FFmpeg/OpenCV) & MP4 export |
| **8** | Optional logo/text overlay |
| **9** | AI inpainting architecture hooks |
| **10** | Hardening, CI, production deploy |

**Current status: Phase 1**

## Quick start (Phase 1)

### Prerequisites

- Node.js 20+
- Python 3.11+
- FFmpeg installed on PATH

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

App: [http://localhost:3000](http://localhost:3000)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### From repo root

```bash
./scripts/dev-frontend.sh
./scripts/dev-backend.sh
```

## Architecture overview

```
Browser (Next.js)
    │  HTTPS / session cookies
    ▼
FastAPI API
    ├── Auth (sessions / JWT — Phase 3)
    ├── Upload & asset store (Phase 4)
    ├── Selection payloads (Phase 6)
    ├── Job queue → FFmpeg / OpenCV workers (Phase 7+)
    └── Export MP4 + optional overlays (Phase 7–8)
```

Future AI inpainting plugs into the same job pipeline as a processing strategy (Phase 9).

## License

Private / all rights reserved. Not for public redistribution of processed third-party media.
