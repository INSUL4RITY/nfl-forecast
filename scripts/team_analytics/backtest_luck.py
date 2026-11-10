"""Does taking turnover luck out of EPA make the matchup expectations predict better? (research tool; changes no report)

Same design as backtest_matchups.py on 2022-25 (FTN charting starts in 2022): fit on weeks 1..W, predict each
offence-against-defence pairing of week W+1 for EPA per play, per dropback and per designed rush. The target is always
the ACTUAL next-week EPA; only the numbers the team effects are fitted on change:

  plain     nflfastR EPA as it is
  fumbles   every offensive fumble gets the average EPA of all offensive fumbles in the window, lost or recovered
            (who recovers a fumble is close to chance)
  turnovers the same, plus every interception-worthy or intercepted throw gets the average EPA of all such throws
            (FTN charting: whether a catchable ball for the defence is caught is close to chance)
  capped    EPA clipped at the 1st and 99th percentile of the window (no charting; limits any single play)

Each version gets its own calibration (the week line of backtest_matchups.py), fitted on the other three seasons.
Differences come with a 95% interval from resampling games.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_luck.py

Result (run 2026-11-10; 1,534 team-games per measure): no version beat plain EPA once calibrated. Error in units of the
league-average error, calibrated, plain / fumbles / turnovers / capped: EPA per play 0.9372 / 0.9373 / 0.9383 / 0.9381;
EPA per dropback 0.9582 / 0.9584 / 0.9593 / 0.9594; EPA per rush 0.9876 / 0.9873 / 0.9873 / 0.9868. Every difference is
within 0.0012 and every 95% interval includes zero. Before calibration, fumble-neutral rushing EPA was better (0.9937
against 0.9999); the calibration already takes that noise out. So the report keeps plain EPA.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backtest_matchups as B  # noqa: E402
import compute as cp  # noqa: E402

SEASONS = range(2022, 2026)
METRICS = [("epa_play", "sc"), ("epa_db", "db"), ("epa_rush", "drush")]
VARIANTS = ["plain", "fumbles", "turnovers", "capped"]


def load(S: int) -> pd.DataFrame:
    P = cp.add_unit_flags(cp.load_pbp(S))
    ftn = cp.fetch(f"ftn_charting/ftn_charting_{S}.parquet")[["nflverse_game_id", "nflverse_play_id", "is_interception_worthy"]]
    P = P.merge(ftn, left_on=["game_id", "play_id"], right_on=["nflverse_game_id", "nflverse_play_id"], how="left")
    P["off_fumble"] = P.sc & (P.fumble == 1) & (P.fumbled_1_team == P.posteam)
    P["int_risk"] = P.sc & ((P.is_interception_worthy == True) | P.int_)   # noqa: E712
    return P


def variants(p: pd.DataFrame) -> pd.DataFrame:
    """The four versions of EPA for one fitting window (averages and percentiles come from that window only)."""
    p = p.copy()
    p["plain"] = p.epa
    p["fumbles"] = np.where(p.off_fumble, p.loc[p.off_fumble, "epa"].mean(), p.epa)
    p["turnovers"] = np.where(p.int_risk & ~p.off_fumble, p.loc[p.int_risk & ~p.off_fumble, "epa"].mean(), p.fumbles)
    lo, hi = p.loc[p.sc, "epa"].quantile([0.01, 0.99])
    p["capped"] = p.epa.clip(lo, hi)
    return p


def predictions() -> pd.DataFrame:
    rows = []
    for S in SEASONS:
        P = load(S)
        teams = sorted(P.posteam.dropna().unique())
        for W in B.WEEKS:
            nx = P[P.week == W + 1]
            if nx.empty:
                continue
            p = variants(P[P.week <= W])
            for name, mask in METRICS:
                d = p[p[mask].astype(bool) & p.epa.notna()]
                x = nx[nx[mask].astype(bool) & nx.epa.notna()]
                g = x.groupby(["game_id", "posteam", "defteam"]).agg(actual=("epa", "mean"), n=("epa", "size"), is_home=("is_home", "first")).reset_index()
                base = cp.adjust(d, "plain", teams)
                g["actual"] = g.actual - base["mean"] - base["home"] * g.is_home
                for v in VARIANTS:
                    a = base if v == "plain" else cp.adjust(d, v, teams)
                    pred = 0
                    for key, eff, col in (("posteam", "off_eff", "posteam"), ("defteam", "def_eff", "defteam")):
                        e = a[eff].reindex(teams)
                        noise = a["resid_var"] / d.groupby(key).size().reindex(teams)
                        tau2 = max(float(e.var(ddof=1) - noise.mean()), 1e-9)
                        pred = pred + g[col].map(e * tau2 / (tau2 + noise)).values
                    rows.append(g.assign(season=S, W=W, metric=name, variant=v, shr=pred)[["season", "W", "metric", "variant", "game_id", "n", "actual", "shr"]])
        print(S, "done", flush=True)
    return pd.concat(rows, ignore_index=True)


def calibrated(R: pd.DataFrame) -> pd.DataFrame:
    """Add each row's out-of-sample calibrated prediction, in units of the measure's league-average error."""
    out = []
    for (m, v), g in R.groupby(["metric", "variant"]):
        sd = B.rmse(g, 0)
        Z = g.assign(actual=g.actual / sd, shr=g.shr / sd)
        Z["cal"] = np.nan
        for s in sorted(Z.season.unique()):
            a, b, k = B.fit(Z[Z.season != s])
            te = Z.season == s
            Z.loc[te, "cal"] = Z.loc[te, "shr"] * B.factor(a, b, Z.loc[te, "W"], k[m])
        out.append(Z)
    return pd.concat(out, ignore_index=True)


def main():
    pd.set_option("display.width", 200)
    Z = calibrated(predictions())
    rng = np.random.default_rng(0)
    print("\nError predicting the actual next-week value (1.0 = expecting the league average; lower is better)")
    for m, _ in METRICS:
        base = Z[(Z.metric == m) & (Z.variant == "plain")].set_index(["season", "game_id", "W"]).sort_index()
        print(f"\n{m}: {len(base)} team-games")
        for v in VARIANTS:
            g = Z[(Z.metric == m) & (Z.variant == v)].set_index(["season", "game_id", "W"]).sort_index()
            line = f"  {v:10s} shrunk {B.rmse(g, g.shr):.4f}  calibrated {B.rmse(g, g.cal):.4f}"
            if v != "plain":
                d = pd.DataFrame({"n": g.n.values, "b": (base.n * (base.actual - base.cal) ** 2).values, "v": (g.n * (g.actual - g.cal) ** 2).values,
                                  "game": [f"{i[0]}_{i[1]}" for i in g.index]})
                gs = d.groupby("game")[["n", "b", "v"]].sum()
                diffs = []
                for _ in range(2000):
                    s = gs.iloc[rng.integers(0, len(gs), len(gs))].sum()
                    diffs.append(np.sqrt(s.v / s.n) - np.sqrt(s.b / s.n))
                lo, hi = np.percentile(diffs, [2.5, 97.5])
                line += f"  vs plain {B.rmse(g, g.cal) - B.rmse(base, base.cal):+.4f} (95% interval {lo:+.4f} to {hi:+.4f})"
            print(line)


if __name__ == "__main__":
    main()
