# Private AI Video Cleaner

Private, owner-only web application for editing videos you have permission to edit.

> **Intended use:** Only process media you own or have explicit rights to edit.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js (TypeScript), Tailwind CSS |
| Backend | FastAPI (Python), SQLAlchemy, Argon2 sessions |
| Media metadata | ffprobe (FFmpeg suite) |
| Future processing | OpenCV + FFmpeg encode (later phases) |

## Current phase

**Phase 4 — Processing engine**

FFmpeg + OpenCV mask-scoped pipeline (blur / fill / classic inpaint), GPU when available, CPU fallback, jobs API + MP4 export. AI removal is not enabled yet.

See [docs/PROCESSING_ENGINE.md](docs/PROCESSING_ENGINE.md), [docs/DEVELOPMENT_PHASES.md](docs/DEVELOPMENT_PHASES.md), and [docs/API_CONTRACT.md](docs/API_CONTRACT.md).

## Repository layout

```
.
├── frontend/          # Next.js app
├── backend/           # FastAPI API
├── shared/            # Shared schema notes
├── docs/              # Architecture & API contract
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

Frontend proxies `/api/*` to the backend (`BACKEND_URL`).

- App: http://localhost:3000
- API docs: http://localhost:8000/docs

### First run

1. Open http://localhost:3000/bootstrap and create the owner account.
2. Sign in at `/login`.
3. Upload at `/upload`, then open `/editor/{videoId}` to select regions.

## Security notes

- HttpOnly session cookie + CSRF token on mutating requests
- Argon2 password hashing
- Auth rate limiting
- Upload extension/MIME/size validation
- Per-user storage isolation

## License

Private / all rights reserved. Not for public redistribution of processed third-party media.
