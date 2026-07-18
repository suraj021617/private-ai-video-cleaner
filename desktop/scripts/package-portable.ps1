#Requires -Version 5.1
<#
.SYNOPSIS
  Assemble a portable Windows folder for Private AI Video Cleaner.
#>

param(
  [string]$OutDir = (Join-Path $PSScriptRoot "..\dist\PrivateAIVideoCleaner")
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "backend") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "frontend") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "storage") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "models") | Out-Null

# Copy runtime trees (exclude virtualenvs / node_modules — rebuild on target or ship separately)
Copy-Item -Recurse -Force (Join-Path $RepoRoot "backend\app") (Join-Path $OutDir "backend\app")
Copy-Item -Force (Join-Path $RepoRoot "backend\requirements.txt") (Join-Path $OutDir "backend\requirements.txt")
Copy-Item -Force (Join-Path $RepoRoot "backend\.env.example") (Join-Path $OutDir "backend\.env.example")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "docs") (Join-Path $OutDir "docs")
Copy-Item -Force (Join-Path $RepoRoot "README.md") (Join-Path $OutDir "README.md")

@"
@echo off
setlocal
cd /d %~dp0
if not exist backend\.venv (
  python -m venv backend\.venv
  call backend\.venv\Scripts\activate.bat
  pip install -r backend\requirements.txt
) else (
  call backend\.venv\Scripts\activate.bat
)
if not exist backend\.env copy backend\.env.example backend\.env
start "PAVC API" cmd /c "uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"
if exist frontend\.next (
  start "PAVC UI" cmd /c "cd frontend && npm run start -- -p 3000"
) else if exist frontend\package.json (
  start "PAVC UI" cmd /c "cd frontend && npm install && npm run build && npm run start -- -p 3000"
)
echo Private AI Video Cleaner starting...
echo UI: http://127.0.0.1:3000
echo API: http://127.0.0.1:8000/docs
"@ | Set-Content -Encoding ASCII (Join-Path $OutDir "Start-PrivateAIVideoCleaner.bat")

@"
{
  "portable": true,
  "autoUpdate": {
    "enabled": true,
    "feedUrl": "https://localhost/updates/pavc/latest.json",
    "checkOnLaunch": true
  },
  "paths": {
    "storage": "./storage",
    "models": "./models"
  }
}
"@ | Set-Content -Encoding UTF8 (Join-Path $OutDir "portable.config.json")

Write-Host "Portable package ready at $OutDir"
