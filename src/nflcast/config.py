"""Project paths and configuration loading."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "configs"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MANUAL_DIR = DATA_DIR / "manual"
REPORTS_DIR = ROOT / "reports"
RELEASES_DIR = ROOT / "releases"
WEB_OUT_DIR = ROOT / "web" / "out"


def load_dotenv(path: Path | None = None) -> list[str]:
    """Load KEY=VALUE lines from the git-ignored project `.env` into os.environ (existing variables win).

    Runs on import, so the scheduled task and every CLI command see local secrets after a restart without
    Windows environment changes. Returns the variable NAMES loaded (never values).
    """
    import os
    p = path or ROOT / ".env"
    loaded = []
    if not p.exists():
        return loaded
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and not os.environ.get(k):
            os.environ[k] = v
            loaded.append(k)
    return loaded


load_dotenv()


@lru_cache(maxsize=1)
def settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_stamp(dt: datetime | None = None) -> str:
    """Filesystem-safe UTC timestamp, e.g. 20260925T141502Z."""
    return (dt or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def release_paths() -> list[Path]:
    """Forecast release files only: releases/<season>/week_<nn>/rel_*.json (never archive manifests or evidence)."""
    return sorted(RELEASES_DIR.glob("[0-9][0-9][0-9][0-9]/week_[0-9][0-9]/rel_*.json"))


RELEASE_PATH_RE = r"^releases/\d{4}/week_\d{2}/rel_[^/]+\.json$"


def ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, MANUAL_DIR, REPORTS_DIR, RELEASES_DIR):
        d.mkdir(parents=True, exist_ok=True)
