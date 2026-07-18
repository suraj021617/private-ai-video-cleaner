#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
if [[ ! -f .env.local && -f .env.example ]]; then
  cp .env.example .env.local || true
fi
npm run dev
