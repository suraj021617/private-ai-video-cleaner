# Backend — Private AI Video Cleaner

FastAPI service for authentication, sessions, secure uploads, metadata, and progress.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
pytest -q
```

## Package layout

```
app/
  main.py
  core/          # settings, security, errors, rate limit
  api/v1/        # auth, uploads, videos, health
  models/        # SQLAlchemy models
  schemas/       # Pydantic contracts
  services/      # auth, upload, storage, probe, video
  db/            # async engine/session
```

## Storage layout

```
storage/
  uploads/{user_id}/{video_id}/source.{ext}
  temp/uploads/{upload_id}/...
  processed/   # reserved for later export phases
```
