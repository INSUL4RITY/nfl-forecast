"""Audit section 2: prediction intervals and win probabilities (verify the existing method; nothing rebuilt).

Method under test = production's (models/probability.py, predict/release.py fit_production): intervals = point forecast +
empirical quantiles of OUT-OF-FOLD residuals of the same model from earlier seasons; P(home win | no tie) = logistic on
the OOF predicted margin. Here, for each test season S in 2019-2024, both are fitted on the walk-forward OOF predictions of
seasons 2017..S-1 only (folds 2017-2018 exist only to give 2019 a calibration set). 2025 is never used.
Models: B_qb (the published Model line, stats only) and C_resid_noinj (market-adjusted line, the primary forecast).
Run: .venv\\Scripts\\python.exe scripts\\audit_2026_11\\s2_distributions.py
"""

import numpy as np
import polars as pl

from common import OUT, games, load, save
from nflcast.evaluation import backtest as BT
from nflcast.models.probability import IntervalModel, OutcomeModel, calibration_table, outcome_scores

LEVELS = (0.5, 0.8, 0.95)
MODELS = ("B_qb", "C_resid_noinj")
data = load("final")
G = games()
preds, _ = BT.run(data, list(range(2017, 2025)), ["final"], specs=[("B_qb", "core_qb", ("final",))],
                  combined_specs=[("C_resid_noinj", "core_qb")])
preds = preds.filter(pl.col("model").is_in(MODELS)).join(
    data.select("game_id", "home_spread", "total"), on="game_id", how="left")
preds.write_parquet(OUT / "s2_oof_predictions.parquet")

rows = []
for m in MODELS:
    p = preds.filter(pl.col("model") == m)
    for S in range(2019, 2025):
        oof, te = p.filter(pl.col("season") < S), p.filter(pl.col("season") == S)
        om = OutcomeModel().fit(oof, G)
        pr = om.predict(te["pred_margin"].to_numpy(), te["is_playoff"].to_numpy())
        g = te.with_columns(p_home=pl.Series(pr["p_home"]), p_away=pl.Series(pr["p_away"]), p_tie=pl.Series(pr["p_tie"]),
                            oof_n=pl.lit(oof.height), oof_seasons=pl.lit(f"{int(oof['season'].min())}-{S-1}"))
        for tgt, pc, ac in (("margin", "pred_margin", "margin"), ("total", "pred_total", "total_points")):
            im = IntervalModel("residual", LEVELS).fit(oof[pc].to_numpy(), oof[ac].to_numpy())
            for lv, (lo, hi) in im.predict(te[pc].to_numpy()).items():
                g = g.with_columns(pl.Series(f"{tgt}_{int(lv*100)}_in", (te[ac].to_numpy() >= lo) & (te[ac].to_numpy() <= hi)),
                                   pl.Series(f"{tgt}_{int(lv*100)}_below", te[ac].to_numpy() < lo),
                                   pl.Series(f"{tgt}_{int(lv*100)}_width", hi - lo))
        rows.append(g)
pg = pl.concat(rows, how="diagonal_relaxed").with_columns(
    spread_bucket=pl.when(pl.col("home_spread").is_null()).then(pl.lit("no line"))
    .when(pl.col("home_spread").abs() <= 3).then(pl.lit("0-3"))
    .when(pl.col("home_spread").abs() <= 7).then(pl.lit("3.5-7"))
    .when(pl.col("home_spread").abs() <= 10).then(pl.lit("7.5-10")).otherwise(pl.lit("10.5+")),
    early=pl.when(pl.col("is_playoff")).then(pl.lit("playoffs")).when(pl.col("week") <= 4).then(pl.lit("weeks 1-4"))
    .otherwise(pl.lit("weeks 5+")),
    res_margin=pl.col("margin") - pl.col("pred_margin"), res_total=pl.col("total_points") - pl.col("pred_total"))
pg.write_parquet(OUT / "s2_per_game.parquet")


def cov_rows(df, by):
    out = []
    for keys, g in df.group_by(by, maintain_order=True):
        n = g.height
        for tgt in ("margin", "total"):
            for lv in LEVELS:
                c = float(g[f"{tgt}_{int(lv*100)}_in"].mean())
                below = float(g[f"{tgt}_{int(lv*100)}_below"].mean())
                se = (lv * (1 - lv) / n) ** 0.5
                out.append({**dict(zip(by, keys)), "target": tgt, "level": lv, "n": n, "coverage": c,
                            "below": below, "above": 1 - c - below, "se": se,
                            "flag": abs(c - lv) > 1.96 * se, "mean_width": float(g[f"{tgt}_{int(lv*100)}_width"].mean())})
    return out


res = {"method": "residual quantiles of earlier-season OOF predictions (as production)", "levels": LEVELS,
       "note_production_levels": "the site publishes 80% and 95% (configs/settings.yaml interval_levels); 50% audited only"}
res["coverage_pooled"] = cov_rows(pg, ["model"])
res["coverage_by_season"] = cov_rows(pg, ["model", "season"])
res["coverage_by_spread"] = cov_rows(pg, ["model", "spread_bucket"])
res["coverage_by_period"] = cov_rows(pg, ["model", "early"])
res["coverage_by_qb_change"] = cov_rows(pg, ["model", "qb_changed"])
res["coverage_by_neutral"] = cov_rows(pg, ["model", "neutral_site"])

# win probabilities
res["outcome_by_season"], res["calibration"] = [], {}
for (m,), g in pg.group_by(["model"], maintain_order=True):
    res["calibration"][m] = calibration_table(g["p_home"].to_numpy(), g["margin"].to_numpy())
    for (S,), gs in g.group_by(["season"], maintain_order=True):
        res["outcome_by_season"].append({"model": m, "season": S, **outcome_scores(
            gs["p_home"].to_numpy(), gs["p_away"].to_numpy(), gs["p_tie"].to_numpy(), gs["margin"].to_numpy())})
    res["outcome_by_season"].append({"model": m, "season": "2019-24", **outcome_scores(
        g["p_home"].to_numpy(), g["p_away"].to_numpy(), g["p_tie"].to_numpy(), g["margin"].to_numpy())})

# symmetry: residual quantiles, overall and from the favourite's side by predicted-margin size
sym = []
for (m,), g in pg.group_by(["model"], maintain_order=True):
    g = g.with_columns(fav_res=pl.when(pl.col("pred_margin") >= 0).then(pl.col("res_margin")).otherwise(-pl.col("res_margin")),
                       size=pl.when(pl.col("pred_margin").abs() < 3).then(pl.lit("<3"))
                       .when(pl.col("pred_margin").abs() < 7).then(pl.lit("3-7"))
                       .when(pl.col("pred_margin").abs() < 10).then(pl.lit("7-10")).otherwise(pl.lit("10+")))
    for (sz,), gs in list(g.group_by(["size"], maintain_order=True)) + [(("all",), g)]:
        r = gs["fav_res"].to_numpy()
        q = np.quantile(r, [0.025, 0.1, 0.25, 0.5, 0.75, 0.9, 0.975])
        boot = np.random.default_rng(1).integers(0, len(r), (2000, len(r)))
        med = np.median(r[boot], axis=1)
        sym.append({"model": m, "pred_margin_size": sz, "n": len(r), "mean": float(r.mean()),
                    "q": dict(zip(["2.5", "10", "25", "50", "75", "90", "97.5"], map(float, q))),
                    "median_ci95": [float(np.quantile(med, .025)), float(np.quantile(med, .975))],
                    "upper_minus_lower_95": float(q[6] + q[0]), "upper_minus_lower_80": float(q[5] + q[1])})
res["symmetry_favourite_side"] = sym
res["n_test_games"] = {m: int(pg.filter(pl.col("model") == m).height) for m in MODELS}
save("s2_distributions", res)

for r in res["coverage_pooled"]:
    print(f"{r['model']:14s} {r['target']:6s} {int(r['level']*100)}%: n={r['n']} cov={r['coverage']:.3f} (below {r['below']:.3f}, above {r['above']:.3f}) width {r['mean_width']:.1f} {'FLAG' if r['flag'] else ''}")
for k in ("coverage_by_season", "coverage_by_spread", "coverage_by_period", "coverage_by_qb_change", "coverage_by_neutral"):
    fl = [r for r in res[k] if r["flag"]]
    print(k, "flags:", [(r["model"], {kk: r[kk] for kk in r if kk in ("season", "spread_bucket", "early", "qb_changed", "neutral_site")},
                          r["target"], r["level"], r["n"], round(r["coverage"], 3)) for r in fl])
for r in res["outcome_by_season"]:
    print(r["model"], r["season"], r["n"], "logloss", round(r["log_loss"], 4), "brier", round(r["brier_home_win"], 4))
for s in sym:
    print(s["model"], s["pred_margin_size"], s["n"], "median", round(s["q"]["50"], 2), s["median_ci95"], "95% tails sum", round(s["upper_minus_lower_95"], 2))
