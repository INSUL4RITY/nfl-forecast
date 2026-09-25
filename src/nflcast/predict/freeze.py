"""Model freeze for the remaining slate.

`freeze(version)` fits the production models once (configs/production.yaml), and saves the fitted objects, probability
calibration, residual-interval samples and QB start-rate tables to artifacts/frozen/<version>/production.joblib. The file's
sha256 and the hashes of every model-relevant configuration are recorded in configs/model_freeze.yaml.
While frozen, every release loads exactly this artifact (load() verifies the sha256); scheduled runs only refresh inputs
(completed games feeding as-of team form, market lines, QB availability, injury display, weather display).
check() is run before each publication: a changed artifact or changed production/settings config blocks publishing.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import joblib
import yaml

from nflcast.config import ROOT, settings, utc_now

FREEZE_FILE = ROOT / "configs" / "model_freeze.yaml"
ART_DIR = ROOT / "artifacts" / "frozen"
WATCHED = ["configs/production.yaml", "configs/settings.yaml"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_frozen() -> bool:
    return FREEZE_FILE.exists()


def freeze(version: str, valid_through: str) -> Path:
    from nflcast.predict.release import fit_production
    if FREEZE_FILE.exists():
        raise SystemExit(f"Already frozen ({yaml.safe_load(FREEZE_FILE.read_text())['version']}); a new version needs an explicit decision.")
    season = settings()["seasons"]["current"]
    M = fit_production(season)
    d = ART_DIR / version
    d.mkdir(parents=True, exist_ok=True)
    art = d / "production.joblib"
    payload = {k: M[k] for k in ("cmod", "bmod", "calib", "alpha_margin", "alpha_total", "alpha_fallback", "oof_models",
                                 "oof_source_run", "qb_rates", "training_games", "last_training_game", "production")}
    joblib.dump(payload, art, compress=3)
    rec = {
        "version": version, "frozen_at_utc": utc_now().isoformat(), "valid_through": valid_through,
        "artifact": art.relative_to(ROOT).as_posix(), "artifact_sha256": _sha(art),
        "watched_configs": {p: _sha(ROOT / p) for p in WATCHED},
        "training": {"games": M["training_games"], "last_training_game": M["last_training_game"],
                     "description": "all completed final-horizon games 2016 through the last game available at freeze time"},
        "production": M["production"], "oof_source_run": M["oof_source_run"], "qb_start_rates": M["qb_rates"]["key"],
        "alphas": {"combined_margin": M["alpha_margin"], "combined_total": M["alpha_total"], "fallback": M["alpha_fallback"]},
        "rules": "Do not refit, retune or change features/configs while frozen. Scheduled runs refresh inputs only.",
    }
    FREEZE_FILE.write_text(yaml.safe_dump(rec, sort_keys=False), encoding="utf-8")
    return FREEZE_FILE


def record() -> dict:
    return yaml.safe_load(FREEZE_FILE.read_text(encoding="utf-8"))


def check() -> list[str]:
    """Problems that must block publication while frozen (empty = OK)."""
    if not is_frozen():
        return []
    r = record()
    probs = []
    art = ROOT / r["artifact"]
    if not art.exists():
        probs.append("frozen artifact missing")
    elif _sha(art) != r["artifact_sha256"]:
        probs.append("frozen artifact changed")
    for p, h in r["watched_configs"].items():
        if _sha(ROOT / p) != h:
            probs.append(f"{p} changed since freeze")
    return probs


def load() -> dict:
    probs = check()
    if probs:
        raise RuntimeError("MODEL FREEZE VIOLATION: " + "; ".join(probs))
    r = record()
    M = joblib.load(ROOT / r["artifact"])
    M.update({"frozen": True, "model_version": r["version"], "artifact_sha256": r["artifact_sha256"]})
    return M
