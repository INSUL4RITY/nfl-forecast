"""Forecast validation and version selection, shared by release writing, scoring and the website export.

A forecast is valid only if every check passes. Invalid forecasts are never published as a headline
forecast, never displayed as the current forecast, and never scored. When a newer version is invalid,
the latest earlier *valid* version remains the current/frozen one.
"""

from __future__ import annotations

import math
from datetime import datetime

VALID_STATUSES = {"ok", "fallback_football_only_no_market_line", "fallback_after_validation_failure"}
TOL = 1e-6


def check_forecast(fc: dict | None, is_playoff: bool) -> list[str]:
    """Return a list of problems (empty = valid)."""
    if not fc:
        return ["missing forecast"]
    p: list[str] = []
    nums = ["home_pts", "away_pts", "margin", "total", "p_home", "p_away", "p_tie"]
    for k in nums:
        v = fc.get(k)
        if v is None or not isinstance(v, (int, float)) or not math.isfinite(v):
            p.append(f"{k} not finite")
    if p:
        return p
    if fc["home_pts"] < 0 or fc["away_pts"] < 0:
        p.append("negative expected points")
    if abs(fc["margin"] - (fc["home_pts"] - fc["away_pts"])) > TOL:
        p.append("margin != home - away")
    if abs(fc["total"] - (fc["home_pts"] + fc["away_pts"])) > TOL:
        p.append("total != home + away")
    probs = [fc["p_home"], fc["p_away"], fc["p_tie"]]
    if any(x < 0 or x > 1 for x in probs):
        p.append("probability outside [0, 1]")
    if abs(sum(probs) - 1) > TOL:
        p.append("probabilities do not sum to 1")
    if is_playoff and fc["p_tie"] != 0:
        p.append("playoff tie probability not zero")
    iv = fc.get("intervals") or {}
    for tgt in ("margin", "total"):
        for lv in ("80", "95"):
            r = iv.get(f"{tgt}_{lv}")
            if not r or len(r) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in r):
                p.append(f"{tgt}_{lv} interval missing")
            elif r[0] > r[1]:
                p.append(f"{tgt}_{lv} interval out of order")
        r80, r95 = iv.get(f"{tgt}_80"), iv.get(f"{tgt}_95")
        if r80 and r95 and (r95[0] > r80[0] + TOL or r95[1] < r80[1] - TOL):
            p.append(f"{tgt} 95% interval does not contain 80% interval")
        if r95 and not (r95[0] - TOL <= fc[tgt] <= r95[1] + TOL):
            p.append(f"{tgt} point forecast outside its 95% interval")
    return p


def entry_is_valid(entry: dict) -> bool:
    return (entry.get("status") in VALID_STATUSES and entry.get("forecast") is not None
            and not check_forecast(entry["forecast"], entry.get("game_type", "REG") != "REG"))


def select_frozen(versions: list[tuple[str, dict]], kickoff: datetime) -> tuple[str, dict] | None:
    """Latest VALID version generated strictly before kickoff. versions: [(generated_at_iso, entry)]."""
    ok = [(t, e) for t, e in versions if datetime.fromisoformat(t) < kickoff and entry_is_valid(e)]
    return max(ok, key=lambda x: x[0]) if ok else None
