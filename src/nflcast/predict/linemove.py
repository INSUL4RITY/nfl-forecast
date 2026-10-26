"""Display only (user request 2026-10-26): how the market line moved after each pick locked, valued with key numbers.

For every finished game with a publicly verifiable locked pick, compare the locked line with the last line we recorded
before kickoff (the final pregame version's line). A move "toward" a side makes that side's position at the locked line
better than at the later line. Points alone undervalue moves through 3 and 7, so each move is also valued as the
change in the chance that the result lands on that side (a push counts half), using:
    P(home margin = k) proportional to Normal(k; mean = -later line, sd) x w_|k|
where w are key-number weights: observed frequency of each final margin divided by the frequency a smooth normal around
the line would give (2016-2025 games with a line; configs/key_numbers.yaml, fitted once). Nothing here changes a pick.
"""

from __future__ import annotations

import json

import numpy as np
import yaml
from scipy.stats import norm

from nflcast.config import PROCESSED_DIR, ROOT

KEY_FILE = ROOT / "configs" / "key_numbers.yaml"
BANDS = [("under_1_5", 0.0, 1.5), ("1_5_to_3", 1.5, 3.0), ("3_plus", 3.0, float("inf"))]
_K = np.arange(-80, 81)


def fit_weights(seasons=(2016, 2025)) -> dict:
    """One-off: key-number weights by |margin| (0..60) from final games with a line, plus the margin sd around the line."""
    import polars as pl
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    mk = pl.read_parquet(PROCESSED_DIR / "market_asof.parquet").filter((pl.col("horizon") == "final") & pl.col("market_available"))
    h = games.filter((pl.col("status") == "final") & pl.col("season").is_between(*seasons)).join(
        mk.select("game_id", "home_spread"), on="game_id")
    m, mu = h["margin"].to_numpy().astype(float), -h["home_spread"].to_numpy().astype(float)
    sd = float(np.std(m - mu))
    exp = np.zeros(len(_K))
    for x in mu:
        exp += norm.cdf(_K + 0.5, x, sd) - norm.cdf(_K - 0.5, x, sd)
    obs = np.array([(m == k).sum() for k in _K], dtype=float)
    w = {}
    for a in range(0, 61):
        o, e = obs[np.abs(_K) == a].sum(), exp[np.abs(_K) == a].sum()
        w[a] = round(float((o + 2.0) / (e + 2.0)), 4)          # +2 pseudo-count keeps rare margins near 1
    return {"seasons": list(seasons), "games": len(m), "sd": round(sd, 4), "weights_by_abs_margin": w,
            "note": "Key-number weights: observed / smooth-normal frequency of each final margin (|margin| > 60 -> 1)."}


_CACHE: dict = {}


def params() -> dict:
    if "p" not in _CACHE:
        _CACHE["p"] = yaml.safe_load(KEY_FILE.read_text(encoding="utf-8"))
    return _CACHE["p"]


def margin_dist(mean: float) -> np.ndarray:
    p = params()
    w = np.array([p["weights_by_abs_margin"].get(abs(int(k)), 1.0) for k in _K])
    d = (norm.cdf(_K + 0.5, mean, p["sd"]) - norm.cdf(_K - 0.5, mean, p["sd"])) * w
    return d / d.sum()


def side_chance(home_spread: float, home_side: bool, dist: np.ndarray) -> float:
    """Chance the result lands on that side of a line (push = half)."""
    t = -home_spread                                  # the home margin that is level with the line
    win = dist[_K > t].sum() if home_side else dist[_K < t].sum()
    return float(win + 0.5 * dist[_K == t].sum())


def move_for(lock_line: float, later_line: float, home_side: bool) -> dict:
    """The move from the locked line to the later line, from that side's point of view."""
    dist = margin_dist(-later_line)
    pts = (lock_line - later_line) * (1 if home_side else -1)      # > 0: the later line is worse for that side
    return {"points_toward": round(pts, 2),
            "chance_gained": round(side_chance(lock_line, home_side, dist) - side_chance(later_line, home_side, dist), 4)}


def _empty() -> dict:
    return {"n": 0, "toward": 0, "against": 0, "unchanged": 0, "points": 0.0, "chance": 0.0}


def _add(acc: dict, mv: dict) -> None:
    acc["n"] += 1
    acc["toward" if mv["points_toward"] > 0 else "against" if mv["points_toward"] < 0 else "unchanged"] += 1
    acc["points"] += mv["points_toward"]
    acc["chance"] += mv["chance_gained"]


def game_moves(item: dict) -> dict | None:
    """Per finished game: the locked line, the last pregame line, and the move for the model pick, the model line
    (stats only) and the v2.1 trial line sides at the lock. None without a publicly verifiable locked line."""
    lk, fc = item.get("locked_pick") or {}, item.get("forecast") or {}
    L0, L1 = lk.get("line_home_spread"), (fc.get("market") or {}).get("home_spread")
    if (item.get("status") != "final" or L0 is None or L1 is None
            or lk.get("verification") != "publicly_verifiable_pregame"):
        return None
    out = {"lock_line": L0, "last_line": L1, "sides": {}}
    lean = lk.get("lean") or {}
    if lean.get("status") == "lean":
        out["sides"]["model_pick"] = {**move_for(L0, L1, lean["side"] == item["home"]), "gap": lean["difference"]}
    for key, src in (("model_line", "stats_only"), ("v2_trial", "stats_v2")):
        m = (lk.get(src) or {}).get("margin")
        if m is not None and abs(m + L0) >= 0.005:
            out["sides"][key] = {**move_for(L0, L1, m + L0 > 0), "gap": abs(m + L0)}
    return out


def summary(items: list[dict]) -> dict:
    """Season totals: model pick, model line by gap band at the lock, v2.1 trial."""
    s = {"model_pick": _empty(), "model_line": _empty(), "v2_trial": _empty(),
         "model_line_bands": {b: _empty() for b, _, _ in BANDS}}
    for it in items:
        mv = it.get("line_move")
        if not mv:
            continue
        for key, x in mv["sides"].items():
            _add(s[key], x)
            if key == "model_line":
                band = next(b for b, lo, hi in BANDS if lo <= x["gap"] < hi)
                _add(s["model_line_bands"][band], x)
    return s


if __name__ == "__main__":
    print(json.dumps(fit_weights(), indent=1))
