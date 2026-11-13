"""Reliability levels shown as badges on the page: how much of a figure is likely to last, from the fitted shrinkage weight.

One scale for the whole page so a badge means the same thing everywhere:
    High   = the weight keeps 50% or more of the figure's gap from average
    Medium = 20% to 50%
    Low    = under 20%
Team measures use the calibrated weight of the matchup models (matchup_models.json); player efficiency uses the per-
opportunity fit in player_shrinkage.json (backtest_player_sample.py), whose weights are far smaller at the same sample.
"""
from __future__ import annotations

import json
from pathlib import Path

HIGH, MEDIUM = 0.5, 0.2
_PS = Path(__file__).resolve().parent / "player_shrinkage.json"
PLAYER = json.loads(_PS.read_text(encoding="utf-8")) if _PS.exists() else None


def level(w) -> str | None:
    if w is None or w != w:
        return None
    return "High" if w >= HIGH else ("Medium" if w >= MEDIUM else "Low")


def player_kept(kind: str, n) -> float | None:
    """Share of a player's per-opportunity EPA gap from average expected to last, at n opportunities.
    kind: 'carry', 'target_WR', 'target_TE' or 'target_RB' (tight ends and other positions use the WR fit)."""
    if not PLAYER or not n:
        return None
    if kind == "target_TE":       # the tight-end fit rests on few cases (8 player-seasons at 80 targets): use the WR fit
        kind = "target_WR"
    m = PLAYER["measures"].get(kind) or PLAYER["measures"]["target_WR"]
    return m["tau2"] / (m["tau2"] + m["s2"] / float(n))
