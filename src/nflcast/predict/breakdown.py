"""Display only: where the football-only (stats-only) projected margin comes from, in plain groups.

The football-only model is a linear ridge on standardised team rows (home offence vs away defence, then away offence vs
home defence), so its projected margin splits exactly into per-feature pieces:
    margin = sum_j coef_j / scale_j * (x_home_row_j - x_away_row_j)
(the intercept and the scaler means cancel). Pieces are averaged over the QB scenarios with the same weights as the
forecast and summed into groups. Nothing here changes a forecast; the groups add up to the published football-only margin.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from nflcast.models.core import stack_team_rows

GROUPS = [("home_field", "Home field"), ("rest", "Rest and schedule"), ("qb", "Quarterbacks"),
          ("passing", "Passing game"), ("rushing", "Running game"), ("efficiency", "Overall efficiency"),
          ("scoring", "Scoring and red zone"), ("turnovers", "Turnovers and field position"),
          ("pace", "Pace and play style"), ("other", "Other")]
_METRIC_GROUP = {"epa_db": "passing", "expl_db": "passing", "sack_rate": "passing",
                 "epa_rush": "rushing", "expl_rush": "rushing",
                 "epa_play": "efficiency", "succ_play": "efficiency", "adj_off_epa": "efficiency", "adj_def_epa": "efficiency",
                 "pts_drive": "scoring", "rz_td": "scoring", "points_pg": "scoring", "adj_off_pts": "scoring",
                 "adj_def_pts": "scoring",
                 "int_rate": "turnovers", "fum_rate": "turnovers", "start_fp": "turnovers",
                 "plays_pg": "pace", "neutral_pass": "pace"}
TOLERANCE = 1e-6


def group_of(name: str) -> str:
    """Group key of a football-only feature column (team_*, opp_* or game context)."""
    base = name.split("_", 1)[1] if name.startswith(("team_", "opp_")) else name
    if base == "venue":
        return "home_field"
    if base in ("rest_adv", "off_bye", "short_week"):
        return "rest"
    if base.startswith("qb_"):
        return "qb"
    if base.startswith("adj_"):
        return _METRIC_GROUP.get(base, "other")
    metric = base[4:] if base.startswith(("off_", "def_")) else base
    return _METRIC_GROUP.get(metric, "other")


def per_feature(bmod, feats: pl.DataFrame) -> tuple[np.ndarray, list[str]]:
    """(n_rows x n_features) margin contributions, positive toward the home team."""
    X, names = stack_team_rows(feats, bmod.feature_set)
    n = feats.height
    sc, r = bmod.pipe[0], bmod.pipe[-1]
    return (X[:n] - X[n:]) / sc.scale_ * r.coef_, names


def football_breakdown(per: np.ndarray, names: list[str], idx: np.ndarray, weights: np.ndarray, margin: float) -> dict | None:
    """Grouped pieces for one game (rows idx = its QB scenarios). None unless they add up to `margin` (the published
    football-only margin); a mismatch would mean the forecast was clipped or the model is not the linear ridge."""
    w = weights / weights.sum()
    ci = per[idx].T @ w
    tot = {k: 0.0 for k, _ in GROUPS}
    for j, nm in enumerate(names):
        tot[group_of(nm)] += float(ci[j])
    if abs(sum(tot.values()) - margin) > TOLERANCE:
        return None
    return {"groups": [{"group": k, "label": lbl, "margin_points": tot[k]} for k, lbl in GROUPS], "margin": margin}
