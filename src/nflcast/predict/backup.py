"""Off-PC backup of prospectively collected data that cannot be re-downloaded later.

Destination: a PRIVATE GitHub repository (default INSUL4RITY/nfl-forecast-data), kept separate from the public project
repository so raw collected data stays private. Local working copy: data/backup_repo/ (git-ignored by the main repo).

Backed up (append-only mirror; files are never deleted from the backup):
  data/raw/weather/**                     weather forecast snapshots per upcoming game (with observation times)
  data/raw/injuries/<season>/**           every injury-report snapshot + checks.jsonl (source of report versions)
  data/processed/injury_versions.parquet  derived injury-report version table
  data/raw/schedules/**                   archived schedule snapshots (the as-of market spread/total history)
  data/raw/odds_api/**                    The Odds API snapshots (point spreads/totals only, no prices) + request log (no key)
verify() checks, via the GitHub API, that the remote repository is private and that every local file is present on the
remote with the identical git blob hash.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from nflcast.config import DATA_DIR, PROCESSED_DIR, RAW_DIR, ROOT, settings, utc_now

REPO = "INSUL4RITY/nfl-forecast-data"
BACKUP_DIR = DATA_DIR / "backup_repo"
NOREPLY = ("INSUL4RITY", "333550074+INSUL4RITY@users.noreply.github.com")
GH = r"C:/Program Files/GitHub CLI/gh.exe"


def _sources() -> list[tuple[Path, str]]:
    season = settings()["seasons"]["current"]
    return [(RAW_DIR / "weather", "raw/weather"), (RAW_DIR / "injuries" / str(season), f"raw/injuries/{season}"),
            (RAW_DIR / "schedules", "raw/schedules"), (RAW_DIR / "odds_api", "raw/odds_api"),(PROCESSED_DIR / "injury_versions.parquet", "processed/injury_versions.parquet")]


def _git(*args: str, cwd: Path = BACKUP_DIR) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _gh(*args: str) -> subprocess.CompletedProcess:
    exe = GH if Path(GH).exists() else "gh"
    return subprocess.run([exe, *args], cwd=ROOT, capture_output=True, text=True)


def configured() -> tuple[bool, str]:
    r = _gh("api", f"repos/{REPO}", "--jq", ".private")
    if r.returncode != 0:
        return False, f"remote repository {REPO} not reachable: {r.stderr.strip()[:200]}"
    if r.stdout.strip() != "true":
        return False, f"remote repository {REPO} is NOT private"
    return True, "ok"


def init(create_remote: bool = False) -> str:
    """Prepare the local working copy; optionally create the PRIVATE remote repository (one-time)."""
    ok, why = configured()
    if not ok and create_remote:
        r = _gh("repo", "create", REPO, "--private", "--description",
                "Private backup of prospectively collected nflcast data (weather snapshots, injury-report versions, line snapshots)")
        if r.returncode != 0:
            return f"could not create {REPO}: {r.stderr.strip()[:300]}"
        ok, why = configured()
    if not ok:
        return why
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if not (BACKUP_DIR / ".git").exists():
        _git("init", "-b", "main")
        _git("config", "user.name", NOREPLY[0])
        _git("config", "user.email", NOREPLY[1])
        _git("config", "core.autocrlf", "false")
        _git("remote", "add", "origin", f"https://github.com/{REPO}.git")
        # authenticate through the GitHub CLI token (works in the scheduled task via GH_TOKEN)
        _git("config", "--add", "credential.https://github.com.helper", "")
        _git("config", "--add", "credential.https://github.com.helper", f'!"{GH}" auth git-credential')
        (BACKUP_DIR / "README.md").write_text(
            "# nflcast private data backup\n\nAppend-only mirror of data collected before each game (cannot be re-downloaded):\n"
            "weather forecast snapshots, injury-report snapshots and version table, schedule/market-line snapshots.\n"
            "Written by `python -m nflcast backup` from the nflcast project. Keep this repository PRIVATE.\n", encoding="utf-8")
    return "ok"


def _mirror() -> dict:
    copied = 0
    for src, dst in _sources():
        if not src.exists():
            continue
        files = [src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]
        for f in files:
            rel = dst if src.is_file() else f"{dst}/{f.relative_to(src).as_posix()}"
            target = BACKUP_DIR / rel
            if target.exists() and target.stat().st_size == f.stat().st_size and \
                    hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(f.read_bytes()).digest():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            copied += 1
    return {"files_copied": copied}


def sync() -> dict:
    status = init(create_remote=False)
    if status != "ok":
        return {"ok": False, "error": status}
    m = _mirror()
    _git("add", "-A")
    if not _git("status", "--porcelain").stdout.strip():
        return {"ok": True, **m, "committed": False, "pushed": False}
    c = _git("commit", "-m", f"Backup {utc_now().isoformat(timespec='minutes')}")
    p = _git("push", "-u", "origin", "HEAD:main")
    return {"ok": p.returncode == 0, **m, "committed": c.returncode == 0, "pushed": p.returncode == 0,
            "push_error": p.stderr.strip()[-300:] if p.returncode else None}


def verify() -> dict:
    """Remote must be private and contain every local file with an identical git blob hash."""
    ok, why = configured()
    if not ok:
        return {"ok": False, "error": why}
    local = {}
    for line in _git("ls-files", "-s").stdout.splitlines():
        meta, path = line.split("\t", 1)
        local[path] = meta.split()[1]
    r = _gh("api", f"repos/{REPO}/git/trees/main?recursive=1")
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr.strip()[:300]}
    remote = {t["path"]: t["sha"] for t in json.loads(r.stdout).get("tree", []) if t["type"] == "blob"}
    missing = [p for p in local if p not in remote]
    differ = [p for p in local if p in remote and remote[p] != local[p]]
    unbacked = []
    for src, dst in _sources():   # every source file must also be in the backup working copy
        files = ([src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]) if src.exists() else []
        for f in files:
            rel = dst if src.is_file() else f"{dst}/{f.relative_to(src).as_posix()}"
            if rel not in local:
                unbacked.append(rel)
    return {"ok": not missing and not differ and not unbacked, "private": True, "remote_files": len(remote),
            "local_files": len(local), "missing_on_remote": missing[:10], "hash_mismatch": differ[:10],
            "not_yet_in_backup": unbacked[:10]}
