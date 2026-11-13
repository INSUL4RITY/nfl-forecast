"""Are coverage, shell, personnel and pass-rush tendencies worth showing, and do they help matchups? Backtest on the
seasons where nflverse participation data has coverage labels (NGS charting, joined to play-by-play).

For each season the regular season is split into weeks 1-9 and 10-18 and three questions are asked:
  1. Tendencies: does a defence's (or offence's) usage rate in the first half predict its rate in the second?
  2. Effects: does a defence's EPA per dropback allowed in a coverage (zone, man, single-high, split-safety) in the first
     half predict the same figure in the second, beyond its overall EPA per dropback allowed?
  3. Matchups: for every second-half team-game, is the offence's dropback EPA predicted better when the offence's own
     first-half results against man and against zone are weighted by the defence's man/zone mix, than by the plain
     offence + defence prediction? Both use the same shrinkage of first-half effects toward the league average.
Writes coverage_backtest.json; the report quotes it in the Method section.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_coverage.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import compute as cp

HERE = Path(__file__).resolve().parent
OUT = HERE / "coverage_backtest.json"
SINGLE_HIGH = {"COVER_1", "COVER_3"}
SPLIT = {"COVER_2", "COVER_4", "COVER_6", "2_MAN"}
K = 150          # shrinkage: an effect on n dropbacks keeps n / (n + K) of its gap from average


def count(series: pd.Series, pos: tuple[str, ...]) -> pd.Series:
    """Players at these positions in a personnel string; handles '4 DL, 2 LB, 5 DB' and '3 CB, 1 FS, 1 SS, ...'."""
    out = pd.Series(0, index=series.index, dtype=float)
    for p in pos:
        out += series.fillna("").str.extract(r"(\d+) " + p + r"(?![A-Z])")[0].astype(float).fillna(0)
    return out.where(series.fillna("") != "")


def season_frame(s: int) -> pd.DataFrame | None:
    part = cp.fetch(f"pbp_participation/pbp_participation_{s}.parquet")
    if "defense_man_zone_type" not in part or part.defense_man_zone_type.replace("", np.nan).notna().sum() < 1000:
        return None
    p = cp.add_unit_flags(cp.load_pbp(s))
    d = p[p.db & p.epa.notna()].merge(part.rename(columns={"nflverse_game_id": "game_id"}), on=["game_id", "play_id"], how="inner")
    mz = d.defense_man_zone_type.replace("", np.nan)
    cov = d.defense_coverage_type.replace("", np.nan)
    d = d.assign(man=mz.eq("MAN_COVERAGE"), zone=mz.eq("ZONE_COVERAGE"), charted=mz.notna(),
                 single=cov.isin(SINGLE_HIGH), split=cov.isin(SPLIT), cov_known=cov.notna(),
                 blitz=d.number_of_pass_rushers >= 5, rush_known=d.number_of_pass_rushers.notna(),
                 pressure=d.was_pressure.fillna(False).astype(bool),
                 nickel=count(d.defense_personnel, ("DB", "CB", "FS", "SS", "S")).eq(5),
                 dime=count(d.defense_personnel, ("DB", "CB", "FS", "SS", "S")).ge(6),
                 pers_known=count(d.defense_personnel, ("DB", "CB", "FS", "SS", "S")).gt(0),
                 p11=count(d.offense_personnel, ("RB", "FB")).eq(1) & count(d.offense_personnel, ("TE",)).eq(1) & count(d.offense_personnel, ("WR",)).eq(3),
                 opers_known=count(d.offense_personnel, ("WR",)).notna(),
                 half=np.where(d.week <= 9, 1, 2), season=s)
    return d[d.season_type == "REG"] if "season_type" in d else d


def rate(d, by, flag, known):
    x = d[d[known]]
    return x.groupby(by)[flag].mean()


def split_corr(d, by, flag, known):
    a = rate(d[d.half == 1], by, flag, known)
    b = rate(d[d.half == 2], by, flag, known)
    j = pd.concat([a, b], axis=1, keys=["h1", "h2"]).dropna()
    return float(j.h1.corr(j.h2)), int(len(j))


def run() -> dict:
    frames = {s: f for s in range(2018, 2026) if (f := season_frame(s)) is not None}
    seasons = sorted(frames)
    out = {"seasons": seasons, "split": "weeks 1-9 vs 10-18", "shrink_k": K, "tendencies": {}, "effects": {}, "matchups": {}}
    tend = [("defence zone rate", "defteam", "zone", "charted"), ("defence man rate", "defteam", "man", "charted"),
            ("defence single-high rate", "defteam", "single", "cov_known"), ("defence split-safety rate", "defteam", "split", "cov_known"),
            ("defence blitz rate (5+ rushers)", "defteam", "blitz", "rush_known"), ("defence nickel rate", "defteam", "nickel", "pers_known"),
            ("defence dime rate", "defteam", "dime", "pers_known"), ("offence 11 personnel rate", "posteam", "p11", "opers_known")]
    for lab, by, flag, known in tend:
        rs = [split_corr(frames[s], by, flag, known) for s in seasons]
        out["tendencies"][lab] = {"corr": round(float(np.nanmean([r[0] for r in rs])), 3), "teams": int(sum(r[1] for r in rs))}
    # pressure rates by rush type
    for lab, m in [("defence pressure rate without blitz", lambda d: d[~d.blitz & d.rush_known]), ("defence pressure rate when blitzing", lambda d: d[d.blitz])]:
        rs = [split_corr(m(frames[s]).assign(k=True), "defteam", "pressure", "k") for s in seasons]
        out["tendencies"][lab] = {"corr": round(float(np.mean([r[0] for r in rs])), 3), "teams": int(sum(r[1] for r in rs))}
    # effects: EPA allowed per dropback in each coverage, and overall
    for lab, mask in [("overall", None), ("in zone", "zone"), ("in man", "man"), ("in single-high", "single"), ("in split-safety", "split")]:
        cs, inc = [], []
        for s in seasons:
            d = frames[s]
            x = d if mask is None else d[d[mask]]
            a, b = x[x.half == 1].groupby("defteam").epa.mean(), x[x.half == 2].groupby("defteam").epa.mean()
            cs.append(float(a.corr(b)))
            if mask:   # does the coverage split add to the overall figure? partial correlation via residuals
                ov1 = d[d.half == 1].groupby("defteam").epa.mean()
                j = pd.concat([a - ov1, b - d[d.half == 2].groupby("defteam").epa.mean()], axis=1, keys=["h1", "h2"]).dropna()
                inc.append(float(j.h1.corr(j.h2)))
        out["effects"][f"EPA/dropback allowed {lab}"] = {"corr": round(float(np.mean(cs)), 3),
                                                         **({"gap_vs_overall_corr": round(float(np.mean(inc)), 3)} if inc else {})}
    # matchups
    err_base, err_cov, w_all = [], [], []
    for s in seasons:
        d = frames[s]
        h1, h2 = d[d.half == 1], d[d.half == 2]
        lg = h1.epa.mean()
        lg_c = {c: h1[h1[c]].epa.mean() for c in ("man", "zone")}

        def eff(g, by, c=None):
            x = g if c is None else g[g[c]]
            st = x.groupby(by).epa.agg(["mean", "size"])
            base = lg if c is None else lg_c[c]
            return ((st["mean"] - base) * st["size"] / (st["size"] + K))
        oe, de = eff(h1, "posteam"), eff(h1, "defteam")
        oc = {c: eff(h1, "posteam", c) for c in ("man", "zone")}
        dc = {c: eff(h1, "defteam", c) for c in ("man", "zone")}
        mix = h1[h1.charted].groupby("defteam").man.mean()
        games = h2.groupby(["game_id", "posteam", "defteam"]).epa.agg(["mean", "size"]).reset_index()
        for r in games.itertuples():
            if r.posteam not in oe or r.defteam not in de or r.defteam not in mix:
                continue
            base = lg + oe[r.posteam] + de[r.defteam]
            m = mix[r.defteam]
            covp = sum(w * (lg_c[c] + oc[c].get(r.posteam, 0) + dc[c].get(r.defteam, 0)) for c, w in (("man", m), ("zone", 1 - m)))
            err_base.append(r.mean - base)
            err_cov.append(r.mean - covp)
            w_all.append(r.size)
    w = np.array(w_all)
    rm = lambda e: float(np.sqrt(np.average(np.square(e), weights=w)))   # noqa: E731
    eb, ec = np.array(err_base), np.array(err_cov)
    rng = np.random.default_rng(1)
    boot = []
    for _ in range(1000):
        i = rng.integers(0, len(w), len(w))
        boot.append(np.sqrt(np.average(np.square(ec[i]), weights=w[i])) - np.sqrt(np.average(np.square(eb[i]), weights=w[i])))
    out["matchups"] = {"team_games": int(len(w)), "rmse_plain": round(rm(eb), 4), "rmse_coverage_mix": round(rm(ec), 4),
                       "difference_ci": [round(float(x), 4) for x in np.percentile(boot, [2.5, 97.5])]}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    res = run()
    print(json.dumps(res, indent=1))
    if a.write:
        OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print("wrote", OUT)
