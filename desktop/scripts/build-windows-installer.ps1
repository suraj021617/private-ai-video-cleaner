#Requires -Version 5.1
<#
.SYNOPSIS
  Build a Windows installer for Private AI Video Cleaner (Inno Setup).

.DESCRIPTION
  Packages the portable app folder and generates a Setup.exe with desktop
  shortcut, Start Menu entry, and optional auto-update stub.
  Requires Inno Setup 6 (ISCC.exe) on PATH or at the default install location.
#>

param(
  [string]$AppVersion = "0.7.0",
  [string]$SourceDir = (Join-Path $PSScriptRoot "..\dist\PrivateAIVideoCleaner"),
  [string]$OutDir = (Join-Path $PSScriptRoot "..\dist\installer"),
  [switch]$PortableOnly
)

$ErrorActionPreference = "Stop"
$IssPath = Join-Path $PSScriptRoot "installer.iss"

if (-not (Test-Path $SourceDir)) {
  Write-Host "Portable app folder missing: $SourceDir"
  Write-Host "Run package-portable.ps1 first."
  exit 1
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if ($PortableOnly) {
  $zip = Join-Path $OutDir "PrivateAIVideoCleaner-$AppVersion-portable.zip"
  if (Test-Path $zip) { Remove-Item $zip -Force }
  Compress-Archive -Path (Join-Path $SourceDir "*") -DestinationPath $zip
  Write-Host "Portable archive: $zip"
  exit 0
}

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
  $default = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
  if (Test-Path $default) { $isccPath = $default }
  else {
    Write-Host "Inno Setup 6 (ISCC.exe) not found. Generating portable zip instead."
    & $PSCommandPath -AppVersion $AppVersion -SourceDir $SourceDir -OutDir $OutDir -PortableOnly
    exit 0
  }
} else {
  $isccPath = $iscc.Source
}

& $isccPath `
  /DAppVersion=$AppVersion `
  /DSourceDir="$SourceDir" `
  /DOutDir="$OutDir" `
  "$IssPath"

Write-Host "Installer build finished. Output: $OutDir"
