"""A2/A3: evaluation exactly as pre-registered (absences_v1_preregistration_2026-11-21.md, sections 2-3).

Builds the candidate inputs (a2_build.py), runs every arm walk-forward on identical games, applies the pass rule and the
secondary analyses, and writes reports/research/absences_v1_evaluation_<UTC>.json + _predictions.parquet.
Run only after the pre-registration's RFC 3161 timestamp (absences_v1_preregistration_2026-11-21.md.tsa.jsonl).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

import a2_build as B  # noqa: E402
from common import locked_games  # noqa: E402
from nflcast.config import PROCESSED_DIR, ROOT  # noqa: E402
from nflcast.evaluation import backtest as BT  # noqa: E402
from nflcast.evaluation.metrics import block_bootstrap_diff, per_game_losses, point_metrics  # noqa: E402
from nflcast.models.core import FootballRidge, feature_set, select_alpha_chronologically  # noqa: E402

PRE = ROOT / "reports" / "research" / "absences_v1_preregistration_2026-11-21.md"
assert (PRE.with_name(PRE.name + ".tsa.jsonl")).exists(), "pre-registration not timestamped"
RD = ROOT / "reports" / "research"
FOLDS, SEEN = [2019, 2020, 2021, 2022, 2023, 2024], [2025, 2026]
REPS, SEED = 2000, 20261121
ARMS = ["AV1", "AV1-inj", "AV1-b8", "AV1-split"]
UNITS = B.UNITS
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# ---------------------------------------------------------------- data
games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
data = BT.assemble(games, pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet"),
                   pl.read_parquet(PROCESSED_DIR / "market_asof.parquet")).filter(pl.col("horizon") == "final")
raw = B.load_raw()
TI, rows, rate_report = B.build(raw, list(range(2016, 2027)))
TI.write_parquet(ROOT / ".scratch" / "a2_team_inputs.parquet")


def with_arm(d: pl.DataFrame, arm: str) -> pl.DataFrame:
    cols = [c for c in TI.columns if c.startswith(arm + "|")]
    part = TI.select("game_id", "team", *[pl.col(c).alias(c.split("|")[1]) for c in cols])
    names = [c.split("|")[1] for c in cols]
    out = d.drop([f"{s}_{n}" for s in ("home", "away") for n in names if f"{s}_{n}" in d.columns])
    for side in ("home", "away"):
        out = out.join(part.rename({"team": f"{side}_id", **{n: f"{side}_{n}" for n in names}}), on=["game_id", f"{side}_id"], how="left")
    return out.with_columns([pl.col(f"{s}_{n}").fill_null(0.0) for s in ("home", "away") for n in names])


fs_v1, fs_inj = feature_set("core_qb"), feature_set("core_qb_inj")
fs_split = {**fs_inj, "opp": fs_inj["opp"] + ["lost_edge", "lost_cb"]}
ARM_DATA = {"v1.0": (data, fs_v1), "inj-cur": (data, fs_inj), "AV1": (with_arm(data, "AV1"), fs_inj),
            "AV1-inj": (with_arm(data, "AV1-inj"), fs_inj), "AV1-b8": (with_arm(data, "AV1-b8"), fs_inj)}
ARM_DATA["AV1-split"] = (with_arm(ARM_DATA["AV1"][0].drop([c for c in ARM_DATA["AV1"][0].columns if c.endswith(("lost_edge", "lost_cb"))]), "AV1"), fs_split)


def frame(te, p, model):
    return te.select("game_id", "season", "week", "is_playoff", "home_score", "away_score", "margin", "total_points",
                     "home_spread", "market_available").with_columns(
        model=pl.lit(model), pred_home=pl.Series(p["home_pts"]), pred_away=pl.Series(p["away_pts"]),
        pred_margin=pl.Series(p["margin"]), pred_total=pl.Series(p["total"]))


info = {}
preds = []
for name, (d, fs) in ARM_DATA.items():
    for S in ([2017, 2018] if name == "v1.0" else []) + FOLDS + SEEN:
        tr = d.filter((pl.col("season") >= 2016) & (pl.col("season") < S))
        te = d.filter((pl.col("season") == S) & pl.col("margin").is_not_null())
        if S == 2026:
            te = te.filter(pl.col("week") <= 11)
        if te.height == 0:
            continue
        a, _ = select_alpha_chronologically(tr, feature_set=fs)
        m = FootballRidge(alpha=a, feature_set=fs).fit(tr)
        preds.append(frame(te, m.predict(te), name))
        info.setdefault(name, {})[S] = {"alpha": a, "n_train": tr.height, "n_test": te.height}
        if S == 2024 or S == 2026:
            coef = dict(zip(m.names, m.pipe[-1].coef_ / m.pipe[0].scale_))
            info[name][S]["lost_coefs"] = {k: float(v) for k, v in coef.items() if "lost_" in k}
P_ = pl.concat(preds)

# v2.2 (existing walk-forward predictions, same folds)
v22 = pl.read_parquet(RD / "v2_2_evaluation_20261027T025629Z_predictions.parquet").filter(pl.col("model") == "B_v2")
v22 = v22.join(P_.filter(pl.col("model") == "v1.0").select("game_id", "home_spread", "market_available"), on="game_id", how="inner",
               suffix="_x").select(P_.columns[:10] if False else ["game_id", "season", "week", "is_playoff", "home_score", "away_score",
                                                                   "margin", "total_points", "home_spread_x", "market_available_x",
                                                                   "pred_home", "pred_away", "pred_margin", "pred_total"])
v22 = v22.rename({"home_spread_x": "home_spread", "market_available_x": "market_available"}).with_columns(model=pl.lit("v2.2"))
# shrink-to-line baseline on v1.0 out-of-fold predictions
v1 = P_.filter(pl.col("model") == "v1.0")
shr, kinfo = [], {}
for S in FOLDS + SEEN:
    h = v1.filter((pl.col("season") < S) & pl.col("market_available"))
    x = (h["pred_margin"] + h["home_spread"]).to_numpy()
    y = (h["margin"] + h["home_spread"]).to_numpy()
    k = float(np.clip((x * y).sum() / (x * x).sum(), 0, 1))
    kinfo[S] = {"k": k, "n": h.height}
    t = v1.filter((pl.col("season") == S) & pl.col("market_available"))
    line = -t["home_spread"]
    pm = line + k * (t["pred_margin"] - line)
    shr.append(t.with_columns(model=pl.lit("shrink-to-line"), pred_margin=pm,
                              pred_home=(t["pred_total"] + pm) / 2, pred_away=(t["pred_total"] - pm) / 2))
ALL = pl.concat([P_.filter(pl.col("season") >= 2019), v22.select(P_.columns), pl.concat(shr).select(P_.columns)], how="vertical_relaxed")
ALL.write_parquet(RD / f"absences_v1_evaluation_{stamp}_predictions.parquet")

MODELS = ["v1.0", "inj-cur", *ARMS, "v2.2", "shrink-to-line"]


def identical(df: pl.DataFrame, seasons: list[int], models: list[str]) -> pl.DataFrame:
    d = df.filter(pl.col("season").is_in(seasons) & pl.col("market_available") & pl.col("model").is_in(models))
    ok = d.group_by("game_id").agg(n=pl.col("model").n_unique()).filter(pl.col("n") == len(models))["game_id"]
    return per_game_losses(d.filter(pl.col("game_id").is_in(ok.to_list())))


def compare(L: pl.DataFrame, a: str, b: str) -> dict:
    A, Bm = L.filter(pl.col("model") == a), L.filter(pl.col("model") == b)
    se = block_bootstrap_diff(A, Bm, "se_margin", REPS, SEED)
    ae = block_bootstrap_diff(A, Bm, "ae_margin", REPS, SEED)
    per = []
    for S in sorted(A["season"].unique().to_list()):
        sa, sb = A.filter(pl.col("season") == S)["se_margin"].mean(), Bm.filter(pl.col("season") == S)["se_margin"].mean()
        per.append({"season": S, "n": A.filter(pl.col("season") == S).height, "mse_a": sa, "mse_b": sb, "better": sa < sb})
    dev = [p for p in per if p["season"] in (2022, 2023, 2024)]
    dev_a = A.filter(pl.col("season").is_in([2022, 2023, 2024]))["se_margin"].mean()
    dev_b = Bm.filter(pl.col("season").is_in([2022, 2023, 2024]))["se_margin"].mean()
    return {"a": a, "b": b, "n_games": se["n_games"], "n_blocks": se["n_blocks"], "mse_a": float(A["se_margin"].mean()),
            "mse_b": float(Bm["se_margin"].mean()), "diff_se": se["mean_diff"], "ci95_se": se["ci95"],
            "diff_ae": ae["mean_diff"], "ci95_ae": ae["ci95"], "mae_a": float(A["ae_margin"].mean()), "mae_b": float(Bm["ae_margin"].mean()),
            "rmse_a": float(np.sqrt(A["se_margin"].mean())), "rmse_b": float(np.sqrt(Bm["se_margin"].mean())),
            "seasons_better": sum(p["better"] for p in per), "per_season": per, "dev_mse_a": dev_a, "dev_mse_b": dev_b,
            "total_mse_a": float(A["se_total"].mean()), "total_mse_b": float(Bm["se_total"].mean())}


L = identical(ALL, FOLDS, MODELS)
res = {"stamp": stamp, "preregistration": PRE.name, "tsa": json.loads(PRE.with_name(PRE.name + ".tsa.jsonl").read_text().splitlines()[0])["tsa_time"],
       "identical_games_2019_24": L["game_id"].n_unique(), "alphas": info, "shrink_k": kinfo, "rates": {str(k): v for k, v in rate_report.items()}}
res["primary"] = {"vs_v1": compare(L, "AV1", "v1.0"), "vs_inj": compare(L, "AV1", "inj-cur")}
p1, p2 = res["primary"]["vs_v1"], res["primary"]["vs_inj"]
checks = {"ci_vs_v1_below_zero": p1["ci95_se"][1] < 0, "ci_vs_inj_below_zero": p2["ci95_se"][1] < 0,
          "seasons_better_vs_inj_ge4": p2["seasons_better"] >= 4, "dev_not_worse_vs_inj": p2["dev_mse_a"] <= p2["dev_mse_b"]}
res["pass_checks"] = checks
res["verdict"] = "PASS" if all(checks.values()) else "FAIL"
res["other_arms"] = {a: {"vs_v1": compare(L, a, "v1.0"), "vs_inj": compare(L, a, "inj-cur")} for a in ARMS if a != "AV1"}
res["reference"] = {f"{a}_vs_v1": compare(L, a, "v1.0") for a in ("inj-cur", "v2.2", "shrink-to-line")}
res["reference"]["AV1_vs_v2.2"] = compare(L, "AV1", "v2.2")
res["reference"]["AV1_vs_shrink"] = compare(L, "AV1", "shrink-to-line")
# seen seasons (reported separately, not pooled)
for S in SEEN:
    ms = ["v1.0", "inj-cur", *ARMS] + (["v2.2", "shrink-to-line"] if S == 2025 else ["shrink-to-line"])
    Ls = identical(ALL, [S], ms)
    res[f"seen_{S}"] = {m: {"n": Ls.filter(pl.col("model") == m).height, "mse": float(Ls.filter(pl.col("model") == m)["se_margin"].mean()),
                            "mae": float(Ls.filter(pl.col("model") == m)["ae_margin"].mean())} for m in ms}
    res[f"seen_{S}_AV1_vs_inj"] = compare(Ls, "AV1", "inj-cur")


# ---------------------------------------------------------------- secondary: C5 slope, gap bins, question 2
def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - h), float(c + h)]


def secondary(df: pl.DataFrame, line_col: str) -> dict:
    out = {}
    for m in df["model"].unique().sort().to_list():
        d = df.filter((pl.col("model") == m) & pl.col(line_col).is_not_null())
        d = d.with_columns(gap=pl.col("pred_margin") + pl.col(line_col), res=pl.col("margin") + pl.col(line_col),
                           big=pl.col(line_col).abs() >= 7)
        o = {}
        for lab, sub in (("all", d), ("spread_lt7", d.filter(~pl.col("big"))), ("spread_ge7", d.filter(pl.col("big")))):
            x, y = sub["gap"].to_numpy(), sub["res"].to_numpy()
            if len(x) < 10:
                continue
            xc = x - x.mean()
            b = float((xc * (y - y.mean())).sum() / (xc ** 2).sum())
            resid = y - y.mean() - b * xc
            se = float(np.sqrt((resid ** 2).sum() / (len(x) - 2) / (xc ** 2).sum()))
            o[lab] = {"n": len(x), "slope": b, "se": se}
        bins = []
        dd = d.filter((pl.col("gap") != 0) & (pl.col("res") != 0)).with_columns(side=(pl.col("gap") > 0) == (pl.col("res") > 0),
                                                                                ag=pl.col("gap").abs())
        for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 99)):
            sub = dd.filter((pl.col("ag") >= lo) & (pl.col("ag") < hi))
            k, n = int(sub["side"].sum()), sub.height
            bins.append({"bin": f"{lo}-{hi if hi < 99 else ''}", "n": n, "model_side": k, "rate": k / n if n else None, "ci95": wilson(k, n)})
        o["gap_bins"] = bins
        out[m] = o
    return out


H = ALL.filter(pl.col("season").is_between(2019, 2025) & pl.col("market_available"))
res["secondary_2019_2025_untimed_lines"] = secondary(H, "home_spread")
lk = locked_games().select("game_id", lock_spread="line_home_spread")
G26 = ALL.filter(pl.col("season") == 2026).join(lk, on="game_id", how="inner")
res["secondary_2026_lock_lines"] = secondary(G26, "lock_spread")
# question 2: in big v1.0 gaps, how much do the new inputs take back (signed towards the gap)
W = (L.filter(pl.col("model").is_in(["v1.0", "AV1", "inj-cur"])).pivot(on="model", index=["game_id", "season", "home_spread"], values="pred_margin")
     .with_columns(gap=pl.col("v1.0") + pl.col("home_spread")))
big = W.filter(pl.col("gap").abs() >= 3)
res["question2_big_gaps_2019_24"] = {"n": big.height, "mean_abs_gap": float(big["gap"].abs().mean()),
                                     "mean_AV1_minus_v1_toward_gap": float(((big["AV1"] - big["v1.0"]) * big["gap"].sign()).mean()),
                                     "mean_inj_minus_v1_toward_gap": float(((big["inj-cur"] - big["v1.0"]) * big["gap"].sign()).mean()),
                                     "share_AV1_reverses": float((((big["AV1"] + big["home_spread"]) * big["gap"].sign()) < 0).mean())}
out = RD / f"absences_v1_evaluation_{stamp}.json"
out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print("verdict", res["verdict"], checks)
for k, c in [("AV1 vs v1.0", p1), ("AV1 vs inj-cur", p2)] + [(f"{a} vs inj-cur", res["other_arms"][a]["vs_inj"]) for a in res["other_arms"]] + \
        [(f"{a} vs v1.0", res["other_arms"][a]["vs_v1"]) for a in res["other_arms"]] + [(k, v) for k, v in res["reference"].items()]:
    print(f"{k:24s} n={c['n_games']} MSE {c['mse_b']:.3f}->{c['mse_a']:.3f} diff {c['diff_se']:+.3f} [{c['ci95_se'][0]:+.3f},{c['ci95_se'][1]:+.3f}] "
          f"MAE {c['mae_b']:.3f}->{c['mae_a']:.3f} better {c['seasons_better']}/6 dev {c['dev_mse_b']:.2f}->{c['dev_mse_a']:.2f}")
print("q2", res["question2_big_gaps_2019_24"])
print("wrote", out.name)
