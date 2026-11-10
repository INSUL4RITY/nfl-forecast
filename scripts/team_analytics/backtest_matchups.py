"""Backtest of the matchup expectations, and the calibration fitted from it.

For every season 2021-25 and every cut week W from 4 to 16, compute.matchup_models is run on weeks 1..W exactly as in
the weekly build (plays, drives and PFR pressure), and each offence-against-defence pairing of week W+1 is predicted
from the uncalibrated shrunk team effects. Compared: the league average, the unshrunk effects and the shrunk
expectation. Also reported: the calibration slope (1.0 = the size of the expected gap is right; below 1 = too extreme)
by cut week, and how often a headline edge of a given size pointed the right way.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_matchups.py                    # report only
    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_matchups.py --write-calibration # also refit matchup_calibration.json

The calibration (see calibration() below) multiplies each shrinkage weight by a factor: one line in the cut week for
all measures, times a scalar per measure (near 0 for a measure whose team effects have not predicted the next game).
It is refitted once a year, after a season ends, never during one.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compute as cp  # noqa: E402

SEASONS = list(range(2021, 2026))
WEEKS = range(4, 17)
EDGE_METRICS = ["epa_db", "epa_rush", "pressure", "expl_pass", "expl_run"]
BUCKETS = ([3, 5, 7, 9, 11, 13, 16], ["4-5", "6-7", "8-9", "10-11", "12-13", "14-16"])
CAL_FILE = Path(__file__).resolve().parent / "matchup_calibration.json"


def season_frames(S: int):
    P = cp.add_unit_flags(cp.load_pbp(S))
    teams = sorted(P.posteam.dropna().unique())
    DR = cp.build_drives(P)
    pfr = cp.fetch(f"pfr_advstats/advstats_week_pass_{S}.parquet")
    pfr = pfr[pfr.game_type == "REG"].assign(team=lambda x: x.team.replace({"LAR": "LA"}), opponent=lambda x: x.opponent.replace({"LAR": "LA"}))
    tg = pfr.groupby(["game_id", "team"]).agg(pressured=("times_pressured", "sum"), opp=("opponent", "first"), week=("week", "first")).reset_index()
    dbg = P[P.db].groupby(["game_id", "posteam"]).size().rename("db").reset_index()
    tg = tg.merge(dbg, left_on=["game_id", "team"], right_on=["game_id", "posteam"], how="left")
    tg = tg[tg.team.isin(teams) & tg.opp.isin(teams)]
    return P, DR, tg, teams


def next_week(name, fr, mask, y, P, DR, tg, W):
    """Actual value, sample size and home sign for each offence-vs-defence pairing in week W + 1."""
    neutral = set(P.loc[P.location == "Neutral", "game_id"])
    if fr == "plays":
        x = P[(P.week == W + 1) & P[mask].astype(bool) & P[y].notna()]
        return x.groupby(["game_id", "posteam", "defteam"]).agg(actual=(y, "mean"), n=(y, "size"), is_home=("is_home", "first")).reset_index()
    if fr == "drives":
        x = DR[(DR.week == W + 1) & ~DR.excluded]
        if mask:
            x = x[x[mask].astype(bool)]
        g = x.groupby(["game_id", "posteam", "defteam"]).agg(actual=(y, "mean"), n=(y, "size"), home=("home_team", "first")).reset_index()
        g["is_home"] = np.where(g.game_id.isin(neutral), 0, np.where(g.posteam == g.home, 1, -1))
        return g
    x = tg[(tg.week == W + 1) & tg.db.notna()]
    homes = P.groupby("game_id").home_team.first()
    g = pd.DataFrame({"game_id": x.game_id, "posteam": x.team, "defteam": x.opp, "actual": x.pressured / x.db, "n": x.db})
    g["is_home"] = np.where(g.game_id.isin(neutral), 0, np.where(g.posteam == g.game_id.map(homes), 1, -1))
    return g


def predictions(seasons=SEASONS) -> pd.DataFrame:
    rows = []
    for S in seasons:
        P, DR, tg, teams = season_frames(S)
        for W in WEEKS:
            if not (P.week == W + 1).any():
                continue
            MM = cp.matchup_models(P[P.week <= W], DR[DR.week <= W], tg[tg.week <= W], teams, calibrate=False)
            for name, fr, mask, y in cp.MATCHUP_METRICS:
                m = MM[name]
                for r in next_week(name, fr, mask, y, P, DR, tg, W).itertuples():
                    o, d = m["off"], m["def"]
                    eo, ed, wo, wd = o["eff"][r.posteam], d["eff"][r.defteam], o["w"][r.posteam], d["w"][r.defteam]
                    rows.append({"season": S, "W": W, "metric": name, "n": r.n, "actual": r.actual - m["mean"] - m["home"] * r.is_home,
                                 "raw": eo + ed, "shr": wo * eo + wd * ed,
                                 "z": wo * eo / np.sqrt(o["tau2"]) + wd * ed / np.sqrt(d["tau2"])})
        print(S, "done", flush=True)
    return pd.DataFrame(rows)


def slope(g: pd.DataFrame, col: str = "shr") -> float:
    return float(np.sum(g.n * g[col] * g.actual) / np.sum(g.n * g[col] * g[col]))


def rmse(g: pd.DataFrame, pred) -> float:
    return float(np.sqrt(np.average((g.actual - pred) ** 2, weights=g.n)))


def standardise(R: pd.DataFrame) -> pd.DataFrame:
    """Put every measure on one scale (its own league-average error) so the measures can be pooled."""
    sd = R.groupby("metric").apply(lambda g: rmse(g, 0), include_groups=False)
    k = R.metric.map(sd)
    return R.assign(actual=R.actual / k, shr=R.shr / k, raw=R.raw / k)


def fit_curve(Z: pd.DataFrame) -> tuple[float, float]:
    """One line for all measures: factor = a + b * W, by weighted least squares of actual on (shr, shr * W)."""
    X = np.column_stack([Z.shr, Z.shr * Z.W]) * np.sqrt(Z.n.values)[:, None]
    a, b = np.linalg.lstsq(X, Z.actual.values * np.sqrt(Z.n.values), rcond=None)[0]
    return float(a), float(b)


K_MAX = 1.5
NOTABLE, SMALL = 1.0, 0.5      # headline-edge sizes reported in the calibration file and on the page


def factor(a: float, b: float, W, k=1.0) -> np.ndarray:
    """k * (a + b * W), kept between 0 and 1: the calibration only ever pulls an expectation towards the league average."""
    return np.clip(np.asarray(k, dtype=float) * (a + b * np.asarray(W, dtype=float)), 0.0, 1.0)


def fit(Z: pd.DataFrame) -> tuple[float, float, pd.Series]:
    """The pooled line, then one scalar per measure: the slope of actual on the line-calibrated expectation."""
    a, b = fit_curve(Z)
    base = Z.assign(base=Z.shr * (a + b * Z.W))
    k = base.groupby("metric").apply(lambda g: float(np.sum(g.n * g.base * g.actual) / np.sum(g.n * g.base * g.base)), include_groups=False)
    return a, b, k.clip(0.0, K_MAX)


def calibration(R: pd.DataFrame) -> dict:
    """The fitted factor by cut week with its out-of-sample check (each season predicted from the other four)."""
    Z = standardise(R)
    a, b, k = fit(Z)
    loso = {}
    for m, g in Z.groupby("metric"):
        e0 = e1 = n = 0.0
        for s in sorted(g.season.unique()):
            aa, bb, kk = fit(Z[Z.season != s])
            te = g[g.season == s]
            e0 += float(np.sum(te.n * (te.actual - te.shr) ** 2))
            e1 += float(np.sum(te.n * (te.actual - te.shr * factor(aa, bb, te.W, kk[m])) ** 2))
            n += float(te.n.sum())
        loso[m] = {"error_before": float(np.sqrt(e0 / n)), "error_after": float(np.sqrt(e1 / n))}
    weeks = list(range(1, 19))
    f = pd.Series([float(factor(a, b, w, k[m])) for m, w in zip(R.metric, R.W)], index=R.index)
    E = R[R.metric.isin(EDGE_METRICS)]
    z = (E.z * f[E.index]).abs()
    right = np.sign(E.z) == np.sign(E.actual)
    edges = {"notable": NOTABLE, "notable_cases": int((z >= NOTABLE).sum()), "notable_right": float(right[z >= NOTABLE].mean()),
             "small": SMALL, "small_cases": int((z < SMALL).sum()), "small_right": float(right[z < SMALL].mean())}
    pooled = Z.assign(weeks=pd.cut(Z.W, BUCKETS[0], labels=BUCKETS[1])).groupby("weeks", observed=True).apply(slope, include_groups=False)
    return {"fitted_on": [int(R.season.min()), int(R.season.max())], "fitted_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "cut_weeks": [int(min(WEEKS)), int(max(WEEKS))], "team_games": int(len(R) / R.metric.nunique()),
            "intercept": a, "per_week": b, "measure_scalar": {m: round(float(v), 3) for m, v in k.items()},
            "factor": {m: {str(w): round(float(factor(a, b, min(max(w, min(WEEKS)), max(WEEKS)), k[m])), 3) for w in weeks} for m in k.index},
            "leave_one_season_out": loso, "edges": edges, "pooled_slope_by_weeks": {str(i): round(float(v), 2) for i, v in pooled.items()},
            "improved": int(sum(v["error_after"] < v["error_before"] for v in loso.values())), "measures": len(loso),
            "note": "Each shrinkage weight is multiplied by factor[measure][through_week] = measure_scalar * (intercept + per_week * week), "
                    "kept between 0 and 1. Error is in units of the league-average error for that measure (below 1 = better than "
                    "expecting the league average). Weeks before 4 use the week 4 factor; weeks after 16 use the week 16 factor."}


def report(R: pd.DataFrame, C: dict | None = None):
    pd.set_option("display.width", 220)
    R = R.assign(weeks=pd.cut(R.W, BUCKETS[0], labels=BUCKETS[1]))
    f = pd.Series([C["factor"][m][str(w)] for m, w in zip(R.metric, R.W)], index=R.index) if C else None
    cal = R.shr * f if C else None
    out = pd.DataFrame({m: {"games": len(g), "rmse_league": rmse(g, 0), "rmse_unshrunk": rmse(g, g.raw), "rmse_shrunk": rmse(g, g.shr),
                            **({"rmse_calibrated": rmse(g, cal[g.index])} if C else {}), "slope_shrunk": slope(g)} for m, g in R.groupby("metric")}).T
    out["shrunk_vs_league_%"] = (1 - out.rmse_shrunk / out.rmse_league) * 100
    if C:
        out["calibrated_vs_league_%"] = (1 - out.rmse_calibrated / out.rmse_league) * 100
    print(out.round(4).to_string())
    print("\nCalibration slope of the shrunk expectation by cut week (1.0 = right size):")
    print(R.groupby(["metric", "weeks"], observed=True).apply(slope, include_groups=False).unstack().round(2).to_string())
    Z = standardise(R).assign(weeks=R.weeks)
    print("all measures pooled:", Z.groupby("weeks", observed=True).apply(slope, include_groups=False).round(2).to_dict())
    E = R[R.metric.isin(EDGE_METRICS)]
    for lab, z in (("uncalibrated", E.z),) + ((("calibrated", E.z * f[E.index]),) if C else ()):
        print(f"\nHeadline edges ({lab}): share pointing the right way")
        for name, q in (("1.5 or more", z.abs() >= 1.5), ("1.0 to 1.5", z.abs().between(1.0, 1.5, inclusive="left")), ("under 0.5", z.abs() < 0.5)):
            g = E[q]
            print(f"  {name}: {len(g)} cases, {(np.sign(z[q]) == np.sign(g.actual)).mean():.1%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-calibration", action="store_true")
    ap.add_argument("--save", help="write the predictions to this parquet file")
    ap.add_argument("--load", help="read predictions from this parquet file instead of recomputing")
    a = ap.parse_args()
    R = pd.read_parquet(a.load) if a.load else predictions()
    if a.save:
        R.to_parquet(a.save)
    C = calibration(R)
    report(R, C)
    print("\nline:", round(C["intercept"], 3), "+", round(C["per_week"], 4), "x week; measure scalars:", C["measure_scalar"])
    print(pd.DataFrame(C["leave_one_season_out"]).T.round(4).to_string())
    print(f"out of sample: lower error on {C['improved']} of {C['measures']} measures")
    if a.write_calibration:
        CAL_FILE.write_text(json.dumps(C, indent=1) + "\n", encoding="utf-8")
        print("wrote", CAL_FILE)


if __name__ == "__main__":
    main()
