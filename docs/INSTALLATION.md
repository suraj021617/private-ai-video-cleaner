# Installation guide

## Prerequisites

- Node.js 20+
- Python 3.11+
- FFmpeg and ffprobe on `PATH`
- Optional: NVIDIA CUDA drivers + PyTorch CUDA build for GPU LaMa

## Fastest: one command

```bash
# Full (LaMa / torch)
./scripts/setup-and-run.sh

# Lite (no torch — Blur / Fill / Classic only)
./scripts/setup-and-run.sh --lite

# Tools check only
./scripts/setup-and-run.sh --check
```

Windows PowerShell:

```powershell
.\scripts\setup-and-run.ps1
.\scripts\setup-and-run.ps1 -Lite
.\scripts\setup-and-run.ps1 -Check
```

Then open http://127.0.0.1:3000/bootstrap

Building from a phone while you wait for a PC: [FROM_MOBILE.md](./FROM_MOBILE.md).

## Manual development install

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt          # or requirements-lite.txt
cp .env.example .env
# For lite: set LITE_MODE=true in .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000 → `/bootstrap` (first run) → `/login` → `/upload`.

## Production notes

- Set a long random `SECRET_KEY`
- Set `COOKIE_SECURE=true` behind HTTPS
- Point `STORAGE_ROOT` and `LAMA_MODEL_DIR` at durable local disks
- Prefer `APP_ENV=production` and `DEBUG=false`

## Windows portable / installer

See [desktop/README.md](../desktop/README.md).

```powershell
cd desktop/scripts
.\package-portable.ps1
.\build-windows-installer.ps1
```

## Model download

LaMa checkpoint downloads automatically into `models/lama/` on first AI job (resumable). ProPainter / STTN activate when their Python packages are installed; otherwise jobs fall back to LaMa → classic inpaint.
