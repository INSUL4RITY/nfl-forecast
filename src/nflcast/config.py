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


@lru_cache(maxsize=1)
def settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_stamp(dt: datetime | None = None) -> str:
    """Filesystem-safe UTC timestamp, e.g. 20260925T141502Z."""
    return (dt or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, MANUAL_DIR, REPORTS_DIR, RELEASES_DIR):
        d.mkdir(parents=True, exist_ok=True)
