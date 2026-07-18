#!/usr/bin/env bash
# One-command local setup + run for Private AI Video Cleaner.
# Usage:
#   ./scripts/setup-and-run.sh           # full (includes torch / LaMa)
#   ./scripts/setup-and-run.sh --lite    # no torch; classic/blur/fill only
#   ./scripts/setup-and-run.sh --check   # dependency check only
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LITE=0
CHECK_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --lite) LITE=1 ;;
    --check) CHECK_ONLY=1 ;;
    -h|--help)
      sed -n '2,7p' "$0"
      exit 0
      ;;
  esac
done

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "MISSING: $1"
    return 1
  fi
  echo "OK: $1 ($(command -v "$1"))"
  return 0
}

echo "== Private AI Video Cleaner — setup =="
echo "Root: $ROOT"
FAIL=0
need python3 || FAIL=1
need node || FAIL=1
need npm || FAIL=1
need ffmpeg || FAIL=1
need ffprobe || FAIL=1

if [[ "$FAIL" -ne 0 ]]; then
  echo ""
  echo "Install missing tools, then re-run."
  echo "  macOS: brew install ffmpeg node python"
  echo "  Ubuntu: sudo apt install ffmpeg nodejs npm python3 python3-venv"
  exit 1
fi

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  echo "All required tools found."
  exit 0
fi

REQ="requirements.txt"
MODE_LABEL="full"
if [[ "$LITE" -eq 1 ]]; then
  REQ="requirements-lite.txt"
  MODE_LABEL="lite"
fi

echo ""
echo "== Backend ($MODE_LABEL) =="
cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r "$REQ"
if [[ ! -f .env ]]; then
  cp .env.example .env
  # unique-ish secret for first run
  SECRET="pavc-$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
  if grep -q '^SECRET_KEY=' .env; then
    sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" .env && rm -f .env.bak
  fi
fi
if [[ "$LITE" -eq 1 ]]; then
  if grep -q '^LITE_MODE=' .env; then
    sed -i.bak 's|^LITE_MODE=.*|LITE_MODE=true|' .env && rm -f .env.bak
  else
    echo 'LITE_MODE=true' >> .env
  fi
fi

echo ""
echo "== Frontend =="
cd "$ROOT/frontend"
if [[ ! -f .env.local && -f .env.example ]]; then
  cp .env.example .env.local
fi
npm install --silent

mkdir -p "$ROOT/storage/uploads" "$ROOT/storage/processed" "$ROOT/storage/temp" "$ROOT/models/lama"

echo ""
echo "== Starting servers =="
echo "  API:  http://127.0.0.1:8000/docs"
echo "  App:  http://127.0.0.1:3000"
echo "  Mode: $MODE_LABEL"
echo "  First visit: http://127.0.0.1:3000/bootstrap"
echo ""

cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

cd "$ROOT/frontend"
npm run dev -- --hostname 127.0.0.1 --port 3000 &
WEB_PID=$!

cleanup() {
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait
