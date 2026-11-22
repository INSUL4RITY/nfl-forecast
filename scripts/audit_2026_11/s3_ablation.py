"""Audit section 3: feature-group ablation of the Model line (football-only ridge, core_qb), refit per fold.

Groups are the ones displayed in "Where the model line comes from" (predict/breakdown.py group_of), with roof (dome)
split out of "other". For each group: drop its columns, refit with chronological alpha, compare per game with the full
model under the decision rule (common.py). Also: leave-one-in (home field + that group only), grouped drops, the
correlation between groups' margin contributions, and baselines (market only, Elo + home field, SRS-style rating + home
field, naive home/away averages). Run: .venv\\Scripts\\python.exe scripts\\audit_2026_11\\s3_ablation.py
"""

import math

import numpy as np
import polars as pl

from common import (FOLDS, OUT, base_fs, decide, fmt_decision, frame, games, live_2026, load, point_metrics, save,
                    walk_forward)
from nflcast.models.core import FootballRidge, MarketRaw, NaiveHome, select_alpha_chronologically
from nflcast.predict.breakdown import group_of

data = load("final")
fs = base_fs()


def grp(name: str) -> str:
    g = group_of(name)
    return "roof" if name == "dome" else g


cols = [("team", f) for f in fs["team"]] + [("opp", f) for f in fs["opp"]] + [("context", f) for f in fs["context"]]
names = {("team", f): f"team_{f}" for f in fs["team"]} | {("opp", f): f"opp_{f}" for f in fs["opp"]} | {("context", f): f for f in fs["context"]}
groups: dict[str, list] = {}
for c in cols:
    groups.setdefault(grp(names[c]), []).append(c)
res = {"groups": {g: [names[c] for c in cs] for g, cs in groups.items()}}


def without(drop: set[str]) -> dict:
    return {k: [f for f in fs[k] if grp(names[(k, f)]) not in drop] for k in ("team", "opp", "context")}


def only(keep: set[str]) -> dict:
    return {k: [f for f in fs[k] if grp(names[(k, f)]) in keep] for k in ("team", "opp", "context")}


info = {}
P = [walk_forward(data, "full", fs, info=info)]
for g in groups:
    P.append(walk_forward(data, f"drop_{g}", without({g}), info=info))
GROUPED = {"drop_scoring+efficiency": {"scoring", "efficiency"}, "drop_passing+rushing": {"passing", "rushing"},
           "drop_scoring+efficiency+passing+rushing": {"scoring", "efficiency", "passing", "rushing"},
           "drop_pace+other+roof+rest": {"pace", "other", "roof", "rest"}}
for nm, s in GROUPED.items():
    P.append(walk_forward(data, nm, without(s), info=info))
for g in groups:
    if g != "home_field":
        P.append(walk_forward(data, f"only_home+{g}", only({"home_field", g}), info=info))
P.append(walk_forward(data, "only_home", only({"home_field"}), info=info))


# ---- baselines on identical games
def naive_frames():
    out = []
    for S in FOLDS:
        tr, te = data.filter((pl.col("season") >= 2016) & (pl.col("season") < S)), data.filter(pl.col("season") == S)
        out.append(frame(te, NaiveHome().fit(tr).predict(te), "baseline_naive_home"))
        te_m = te.filter(pl.col("market_available"))
        out.append(frame(te_m, MarketRaw().predict(te_m), "baseline_market_only"))
    return out


def elo_frames():
    """538-style NFL Elo, parameters fixed a priori (K=20, home 48 Elo pts, MOV multiplier, 1/3 reversion per season),
    run from 2011 on final scores only (each game's rating uses only earlier games). Margin = Elo diff / 25; total =
    training-period mean total."""
    G = games().filter((pl.col("season") >= 2011) & (pl.col("status") == "final")).sort("kickoff_utc", "game_id")
    elo, last_season, pre = {}, None, {}
    for r in G.iter_rows(named=True):
        if r["season"] != last_season:
            elo = {t: 1505 + (e - 1505) * 2 / 3 for t, e in elo.items()}
            last_season = r["season"]
        h, a = elo.get(r["home_team"], 1505.0), elo.get(r["away_team"], 1505.0)
        hfa = 0.0 if r["neutral_site"] else 48.0
        diff = h + hfa - a
        pre[r["game_id"]] = diff
        mov = r["home_score"] - r["away_score"]
        exp_h = 1 / (1 + 10 ** (-diff / 400))
        res_h = 1.0 if mov > 0 else 0.0 if mov < 0 else 0.5
        wdiff = diff if mov > 0 else -diff
        mult = math.log(abs(mov) + 1) * 2.2 / (wdiff * 0.001 + 2.2) if mov != 0 else 1.0
        sh = 20 * mult * (res_h - exp_h)
        elo[r["home_team"]], elo[r["away_team"]] = h + sh, a - sh
    out = []
    for S in FOLDS:
        tr, te = data.filter((pl.col("season") >= 2016) & (pl.col("season") < S)), data.filter(pl.col("season") == S)
        T = float(tr["total_points"].mean())
        M = np.array([pre[g] / 25.0 for g in te["game_id"].to_list()])
        Tt = np.full(te.height, T)
        out.append(frame(te, {"home_pts": (Tt + M) / 2, "away_pts": (Tt - M) / 2, "margin": M, "total": Tt}, "baseline_elo"))
    return out


def srs_frames():
    """SRS-style: as-of opponent-adjusted points ratings (adj_off_pts + adj_def_pts per team) + home field, OLS."""
    out = []
    from sklearn.linear_model import LinearRegression

    def X(d):
        r = (d["home_adj_off_pts"] + d["home_adj_def_pts"] - d["away_adj_off_pts"] - d["away_adj_def_pts"]).to_numpy()
        v = np.where(d["neutral_site"].to_numpy(), 0.0, 1.0)
        return np.column_stack([r, v])
    for S in FOLDS:
        tr, te = data.filter((pl.col("season") >= 2016) & (pl.col("season") < S)), data.filter(pl.col("season") == S)
        m = LinearRegression().fit(X(tr), tr["margin"].to_numpy())
        M = m.predict(X(te))
        Tt = np.full(te.height, float(tr["total_points"].mean()))
        out.append(frame(te, {"home_pts": (Tt + M) / 2, "away_pts": (Tt - M) / 2, "margin": M, "total": Tt}, "baseline_srs"))
    return out


P += naive_frames() + elo_frames() + srs_frames()
preds = pl.concat(P)
preds.write_parquet(OUT / "s3_predictions.parquet")

res["drop_one"] = [decide(preds, f"drop_{g}", "full") for g in groups]
res["drop_grouped"] = [decide(preds, nm, "full") for nm in GROUPED]
res["leave_one_in"] = [decide(preds, f"only_home+{g}", "only_home") for g in groups if g != "home_field"]
res["leave_one_in_vs_full"] = [decide(preds, f"only_home+{g}", "full") for g in groups if g != "home_field"]
res["baselines"] = [decide(preds, "full", b) for b in ("baseline_market_only", "baseline_elo", "baseline_srs", "baseline_naive_home")]
res["drop_one_totals"] = [decide(preds, f"drop_{g}", "full", loss="ae_total") for g in groups]

# ---- correlation between groups' margin contributions (full model, each fold's fit applied to its test season)
contribs = []
for S in FOLDS:
    tr, te = data.filter((pl.col("season") >= 2016) & (pl.col("season") < S)), data.filter(pl.col("season") == S)
    m = FootballRidge(alpha=info["full"][S]["alpha"], feature_set=fs).fit(tr)
    from nflcast.predict.breakdown import per_feature
    per, nms = per_feature(m, te)
    gsum = {}
    for j, nm in enumerate(nms):
        gsum.setdefault(grp(nm), np.zeros(te.height))
        gsum[grp(nm)] += per[:, j]
    contribs.append(pl.DataFrame(gsum).with_columns(season=pl.lit(S)))
C = pl.concat(contribs)
gl = [c for c in C.columns if c != "season"]
corr = np.corrcoef(C.select(gl).to_numpy().T)
res["contribution_corr"] = {"groups": gl, "matrix": corr.round(3).tolist()}
res["contribution_mean_abs"] = {g: float(C[g].abs().mean()) for g in gl}
res["contribution_sd"] = {g: float(C[g].std()) for g in gl}

# ---- 2026 live check for drop-one variants (train 2016-2024)
L = [live_2026(data, "full", fs)] + [live_2026(data, f"drop_{g}", without({g})) for g in groups]
L = pl.concat(L)
res["live_2026"] = {v: point_metrics(L.filter(pl.col("model") == v)) for v in L["model"].unique().sort().to_list()}

save("s3_ablation", res)
print("groups:", {g: len(c) for g, c in groups.items()})
for k in ("drop_one", "drop_grouped", "leave_one_in", "baselines", "drop_one_totals"):
    print("==", k)
    for d in res[k]:
        print("  " + fmt_decision(d))
print("mean |contribution| (margin pts):", {g: round(v, 2) for g, v in res["contribution_mean_abs"].items()})
print("corr groups:", gl)
print(np.array(res["contribution_corr"]["matrix"]))
print("2026 live:", {k: (v["n_games"], round(v["margin_mae"], 3)) for k, v in res["live_2026"].items()})
