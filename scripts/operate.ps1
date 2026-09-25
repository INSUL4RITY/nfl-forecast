# Scheduled entry point (Windows). Runs one operation cycle; safe to call every 30 minutes.
# Register with Task Scheduler only after reviewing: see docs/operations.md.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
$env:NEXT_TELEMETRY_DISABLED = "1"
Set-Location $root
# The GitHub CLI token lives in Windows Credential Manager; expose it to gh and to git's gh credential helper
# (the task's session may not see gh's hosts.yml). Nothing is written to disk.
try { $tok = & gh auth token 2>$null; if ($LASTEXITCODE -eq 0 -and $tok) { $env:GH_TOKEN = $tok.Trim() } } catch { }
# Never block an unattended run on an interactive credential prompt.
$env:GIT_TERMINAL_PROMPT = "0"
$env:GCM_INTERACTIVE = "never"
& "$root\.venv\Scripts\python.exe" -m nflcast operate
