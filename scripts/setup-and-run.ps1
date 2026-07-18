# One-command Windows setup + run for Private AI Video Cleaner.
# Usage:
#   .\scripts\setup-and-run.ps1
#   .\scripts\setup-and-run.ps1 -Lite
#   .\scripts\setup-and-run.ps1 -Check

param(
  [switch]$Lite,
  [switch]$Check
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

function Test-Cmd($Name) {
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if (-not $cmd) {
    Write-Host "MISSING: $Name"
    return $false
  }
  Write-Host "OK: $Name ($($cmd.Source))"
  return $true
}

Write-Host "== Private AI Video Cleaner — setup =="
Write-Host "Root: $Root"

$ok = $true
foreach ($c in @("python", "node", "npm", "ffmpeg", "ffprobe")) {
  if (-not (Test-Cmd $c)) { $ok = $false }
}
if (-not $ok) {
  Write-Host ""
  Write-Host "Install missing tools (Python 3.11+, Node 20+, FFmpeg), then re-run."
  exit 1
}
if ($Check) {
  Write-Host "All required tools found."
  exit 0
}

$Req = if ($Lite) { "requirements-lite.txt" } else { "requirements.txt" }
$Mode = if ($Lite) { "lite" } else { "full" }

Write-Host ""
Write-Host "== Backend ($Mode) =="
Set-Location (Join-Path $Root "backend")
if (-not (Test-Path ".venv")) {
  python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q --upgrade pip
& .\.venv\Scripts\pip.exe install -q -r $Req
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}
if ($Lite) {
  $envText = Get-Content ".env" -Raw
  if ($envText -match "LITE_MODE=") {
    $envText = $envText -replace "LITE_MODE=.*", "LITE_MODE=true"
  } else {
    $envText = $envText.TrimEnd() + "`r`nLITE_MODE=true`r`n"
  }
  Set-Content -Path ".env" -Value $envText -NoNewline
}

Write-Host ""
Write-Host "== Frontend =="
Set-Location (Join-Path $Root "frontend")
if (-not (Test-Path ".env.local") -and (Test-Path ".env.example")) {
  Copy-Item ".env.example" ".env.local"
}
npm install --silent

New-Item -ItemType Directory -Force -Path @(
  (Join-Path $Root "storage\uploads"),
  (Join-Path $Root "storage\processed"),
  (Join-Path $Root "storage\temp"),
  (Join-Path $Root "models\lama")
) | Out-Null

Write-Host ""
Write-Host "== Starting servers =="
Write-Host "  API:  http://127.0.0.1:8000/docs"
Write-Host "  App:  http://127.0.0.1:3000"
Write-Host "  Mode: $Mode"
Write-Host "  First visit: http://127.0.0.1:3000/bootstrap"

$backend = Start-Process -PassThru -WindowStyle Normal -FilePath (Join-Path $Root "backend\.venv\Scripts\uvicorn.exe") -ArgumentList @("app.main:app","--host","127.0.0.1","--port","8000") -WorkingDirectory (Join-Path $Root "backend")
$frontend = Start-Process -PassThru -WindowStyle Normal -FilePath "npm" -ArgumentList @("run","dev","--","--hostname","127.0.0.1","--port","3000") -WorkingDirectory (Join-Path $Root "frontend")

Write-Host "Started. Close those windows or press Ctrl+C here after stopping processes."
Write-Host "Backend PID=$($backend.Id) Frontend PID=$($frontend.Id)"
Wait-Process -Id $backend.Id,$frontend.Id
