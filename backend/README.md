# Backend — Private AI Video Cleaner

FastAPI + FFmpeg + OpenCV (media libs installed; pipeline wired in later phases).

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API root: http://localhost:8000
- Health: http://localhost:8000/api/v1/health
- Ready: http://localhost:8000/api/v1/ready
- OpenAPI: http://localhost:8000/docs

## Package layout

```
app/
  main.py              # FastAPI factory
  core/                # settings, logging, security stubs
  api/v1/endpoints/    # versioned HTTP routes
  schemas/             # Pydantic models & enums
  services/            # business logic placeholders
  workers/             # ffmpeg / opencv / ai stubs
  models/              # ORM models (later)
  db/                  # database session (later)
```

Phase 1 exposes health/readiness only.
