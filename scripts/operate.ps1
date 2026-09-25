# Scheduled entry point (Windows). Runs one operation cycle; safe to call every 30 minutes.
# Register with Task Scheduler only after reviewing: see docs/operations.md.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
$env:NEXT_TELEMETRY_DISABLED = "1"
Set-Location $root
& "$root\.venv\Scripts\python.exe" -m nflcast operate
