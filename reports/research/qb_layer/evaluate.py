"""QB layer evaluation, as pre-registered (reports/research/qb_layer_v2_3_preregistration_2026-11-23.md).

Writes reports/research/qb_layer_v2_3_evaluation_<UTC>.json and _predictions.parquet.
Run from the worktree root with PYTHONPATH=src, after the pre-registration's RFC 3161 timestamp.
Needs .scratch/feature_snapshots_v22_rebuilt.parquet (features/v2.build_snapshots on the same data as the QB layer;
the stored v2.2 file dates from 27 Oct 2026, before the current starter rule).
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

import build as B  # noqa: E402
from nflcast.config import PROCESSED_DIR, ROOT  # noqa: E402
from nflcast.evaluation import backtest as BT  # noqa: E402
from nflcast.evaluation.metrics import block_bootstrap_diff, per_game_losses  # noqa: E402
from nflcast.models.core import FootballRidge, feature_set, select_alpha_chronologically  # noqa: E402

PRE = ROOT / "reports" / "research" / "qb_layer_v2_3_preregistration_2026-11-23.md"
TSA = PRE.with_name(PRE.name + ".tsa.jsonl")
assert TSA.exists(), "pre-registration not timestamped"
RD = ROOT / "reports" / "research"
FOLDS, SEEN, TUNE, DEV = [2019, 2020, 2021, 2022, 2023, 2024], [2025, 2026], [2019, 2020, 2021], [2022, 2023, 2024]
REPS, SEED = 2000, 20261123
NEW = ["qbs_share", "qbs_db_gap", "qb_cpoe", "qb_cpoe_delta"]
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
t0 = time.time()


def log(*a):
    print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)


# ---------------------------------------------------------------- data
games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
market = pl.read_parquet(PROCESSED_DIR / "market_asof.parquet")
V1 = BT.assemble(games, pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet"), market).filter(pl.col("horizon") == "final")
V22 = BT.assemble(games, pl.read_parquet(ROOT / ".scratch" / "feature_snapshots_v22_rebuilt.parquet"), market).filter(pl.col("horizon") == "final")
V22S = BT.assemble(games, pl.read_parquet(PROCESSED_DIR / "feature_snapshots_v22.parquet"), market).filter(pl.col("horizon") == "final")
ids = set(V1["game_id"]) & set(V22["game_id"]) & set(V22S["game_id"])
V1, V22, V22S = (d.filter(pl.col("game_id").is_in(list(ids))).sort("game_id") for d in (V1, V22, V22S))

ctx = B.context()
T = B.targets()
GRID = [B.Cfg(runs=True, opp=True, ped=True, hl=h, carry=c, k=k) for h in (8.0, 16.0, 32.0) for c in (0.6, 0.8, 1.0) for k in (100.0, 250.0, 500.0)]
CFGS = [B.Cfg(), B.Cfg(runs=True, opp=True), B.Cfg(ped=True)] + GRID           # GRID contains the default "ROD"
TI = B.build(ctx, CFGS, T)
CAR = B.career_dropbacks(ctx, T)
TI.write_parquet(ROOT / ".scratch" / "qb_layer_inputs.parquet")
log("built inputs", TI.shape)
# builder check (pre-registered): the rebuilt current rating reproduces the stored v1.0 QB columns
chk = {}
for s in ("home", "away"):
    j = V1.select("game_id", pl.col(f"{s}_id").alias("team"), *[pl.col(f"{s}_{c}").alias(c) for c in ("qb_rating", "qb_log_db", "qb_delta")]).join(TI, on=["game_id", "team"])
    chk[s] = {c: float((j[c] - j[f"cur|{c}"]).abs().max()) for c in ("qb_rating", "qb_log_db", "qb_delta")}
assert all(v < 1e-9 for d in chk.values() for v in d.values()), chk
log("builder check", chk)


def apply(d: pl.DataFrame, cfg: str | None, extra: list[str]) -> pl.DataFrame:
    """Replace the QB rating columns with configuration `cfg` (None: keep) and add `extra` layer columns."""
    cols = (["qb_rating", "qb_log_db", "qb_delta"] if cfg else []) + extra
    src = {c: (f"{cfg}|{c}" if c.startswith("qb_") and cfg else (f"cur|{c}" if c.startswith("qb_cpoe") else c)) for c in cols}
    part = TI.select("game_id", "team", *[pl.col(v).alias(k) for k, v in src.items()])
    out = d.drop([f"{s}_{c}" for s in ("home", "away") for c in cols if f"{s}_{c}" in d.columns])
    for s in ("home", "away"):
        out = out.join(part.rename({"team": f"{s}_id", **{c: f"{s}_{c}" for c in cols}}), on=["game_id", f"{s}_id"], how="left")
    if "home_qb_exp" in out.columns:
        out = out.with_columns([(pl.col(f"{s}_qb_rating") * pl.col(f"{s}_qb_log_db")).alias(f"{s}_qb_exp") for s in ("home", "away")])
    return out


def plus(fs: dict, extra: list[str]) -> dict:
    return {**fs, "team": fs["team"] + extra}


def cfg_ql(c: B.Cfg) -> str:
    return c.name


FS1, FS22 = feature_set("core_qb"), feature_set("v2.2")
QLN = B.Cfg(runs=True, opp=True, ped=True).name                      # "ROD"
ARMS = {
    "v1.0": (V1, FS1),
    "v2.2": (V22, FS22),
    "v2.2-stored": (V22S, FS22),
    "QL": (apply(V22, QLN, NEW), plus(FS22, NEW)),
    "QL-B1": (apply(V22, None, NEW[:2]), plus(FS22, NEW[:2])),
    "QL-B3": (apply(V22, "RO", []), FS22),
    "QL-B27": (apply(V22, "D", []), FS22),
    "QL-B4": (apply(V22, None, NEW[2:]), plus(FS22, NEW[2:])),
    "v1.0+QL": (apply(V1, QLN, NEW), plus(FS1, NEW)),
}


def frame(te, p, model):
    return te.select("game_id", "season", "week", "is_playoff", "home_id", "away_id", "home_score", "away_score", "margin",
                     "total_points", "home_spread", "market_available").with_columns(
        model=pl.lit(model), pred_home=pl.Series(p["home_pts"]), pred_away=pl.Series(p["away_pts"]),
        pred_margin=pl.Series(p["margin"]), pred_total=pl.Series(p["total"]))


def walk(d, fs, name, seasons):
    out, info = [], {}
    for S in seasons:
        tr = d.filter((pl.col("season") >= 2016) & (pl.col("season") < S))
        te = d.filter((pl.col("season") == S) & pl.col("margin").is_not_null())
        if te.height == 0:
            continue
        a, _ = select_alpha_chronologically(tr, feature_set=fs)
        m = FootballRidge(alpha=a, feature_set=fs).fit(tr)
        out.append(frame(te, m.predict(te), name))
        coef = dict(zip(m.names, m.pipe[-1].coef_ / m.pipe[0].scale_))
        info[S] = {"alpha": a, "n_train": tr.height, "n_test": te.height,
                   "qb_coefs": {k: float(v) for k, v in coef.items() if "qb" in k}}
    return pl.concat(out), info


# ---------------------------------------------------------------- B32 tuning (folds 2019-2021 only)
tune = {}
for c in GRID:
    d = apply(V22, c.name, NEW)
    p, _ = walk(d, plus(FS22, NEW), c.name, TUNE)
    tune[c.name] = {"hl": c.hl, "carry": c.carry, "k": c.k, "mse": float(per_game_losses(p)["se_margin"].mean())}
cur = tune[QLN]["mse"]
best = min(tune, key=lambda n: tune[n]["mse"])
if tune[best]["mse"] > cur - 0.01:
    best = QLN
log("tuning", best, round(tune[best]["mse"], 3), "default", round(cur, 3))
ARMS["QL-tuned"] = (apply(V22, best, NEW), plus(FS22, NEW))

preds, info = [], {}
for name, (d, fs) in ARMS.items():
    p, inf = walk(d, fs, name, FOLDS + SEEN)
    preds.append(p)
    info[name] = inf
    log("walk", name)
ALL = pl.concat(preds)
ALL.write_parquet(RD / f"qb_layer_v2_3_evaluation_{stamp}_predictions.parquet")


# ---------------------------------------------------------------- comparisons
def identical(df, seasons, models, market_only=False):
    d = df.filter(pl.col("season").is_in(seasons) & pl.col("model").is_in(models))
    if market_only:
        d = d.filter(pl.col("market_available"))
    ok = d.group_by("game_id").agg(n=pl.col("model").n_unique()).filter(pl.col("n") == len(models))["game_id"]
    return per_game_losses(d.filter(pl.col("game_id").is_in(ok.to_list())))


def compare(L, a, b):
    A, Bm = L.filter(pl.col("model") == a), L.filter(pl.col("model") == b)
    if A.height == 0:
        return None
    se = block_bootstrap_diff(A, Bm, "se_margin", REPS, SEED)
    ae = block_bootstrap_diff(A, Bm, "ae_margin", REPS, SEED)
    te = block_bootstrap_diff(A, Bm, "se_total", REPS, SEED)
    per = []
    for S in sorted(A["season"].unique().to_list()):
        sa, sb = A.filter(pl.col("season") == S)["se_margin"].mean(), Bm.filter(pl.col("season") == S)["se_margin"].mean()
        per.append({"season": S, "n": A.filter(pl.col("season") == S).height, "mse_a": sa, "mse_b": sb, "better": sa < sb})
    dv = lambda X: float(X.filter(pl.col("season").is_in(DEV))["se_margin"].mean()) if X.filter(pl.col("season").is_in(DEV)).height else None  # noqa: E731
    return {"a": a, "b": b, "n_games": se["n_games"], "mse_a": float(A["se_margin"].mean()), "mse_b": float(Bm["se_margin"].mean()),
            "diff_se": se["mean_diff"], "ci95_se": se["ci95"], "diff_ae": ae["mean_diff"], "ci95_ae": ae["ci95"],
            "mae_a": float(A["ae_margin"].mean()), "mae_b": float(Bm["ae_margin"].mean()),
            "total_mse_a": float(A["se_total"].mean()), "total_mse_b": float(Bm["se_total"].mean()),
            "diff_total_se": te["mean_diff"], "ci95_total_se": te["ci95"],
            "seasons_better": sum(p["better"] for p in per), "n_seasons": len(per), "per_season": per,
            "dev_mse_a": dv(A), "dev_mse_b": dv(Bm)}


MODELS = list(ARMS)
L = identical(ALL, FOLDS, MODELS)
res = {"stamp": stamp, "preregistration": PRE.name, "tsa": json.loads(TSA.read_text().splitlines()[0])["tsa_time"],
       "builder_check_max_abs_diff": chk, "n_games_2019_24": L["game_id"].n_unique(), "fits": info,
       "tuning_2019_21": {"chosen": best, "grid": tune}}
p = compare(L, "QL", "v2.2")
checks = {"ci_below_zero": p["ci95_se"][1] < 0, "seasons_better_ge4": p["seasons_better"] >= 4,
          "dev_not_worse": p["dev_mse_a"] <= p["dev_mse_b"]}
res["primary"] = p
res["pass_checks"] = checks
res["verdict"] = "PASS" if all(checks.values()) else "FAIL"
res["arms_vs_v2.2"] = {a: compare(L, a, "v2.2") for a in MODELS if a not in ("v2.2",)}
res["arms_vs_v1.0"] = {a: compare(L, a, "v1.0") for a in ("v2.2", "QL", "v1.0+QL")}
res["market_games_2019_24"] = {a: compare(identical(ALL, FOLDS, MODELS, True), a, "v2.2") for a in ("QL", "v1.0")}
for S in SEEN:
    Ls = identical(ALL, [S], MODELS)
    res[f"seen_{S}"] = {"n": Ls["game_id"].n_unique(),
                        "mse": {m: float(Ls.filter(pl.col("model") == m)["se_margin"].mean()) for m in MODELS},
                        "QL_vs_v2.2": compare(Ls, "QL", "v2.2"), "v1.0+QL_vs_v1.0": compare(Ls, "v1.0+QL", "v1.0")}
log("verdict", res["verdict"], checks)

# ---------------------------------------------------------------- subsets (2019-2024 folds, and 2025 seen)
side = (T.join(CAR, on=["game_id", "team"]).join(TI.select("game_id", "team", "prev_starter", "qbs_share", "cur|qb_delta"), on=["game_id", "team"])
        .with_columns(change=(pl.col("prev_starter").is_not_null() & (pl.col("prev_starter") != pl.col("qb_id"))),
                      newc=pl.col("career_db") < 200)
        .with_columns(backup=pl.col("change") & pl.col("newc"), late=pl.col("newc") & pl.col("bucket").is_in(["R47", "UDFA"])))
gflag = side.group_by("game_id").agg(*[pl.col(f).any().alias(f) for f in ("change", "newc", "backup", "late")])


def subset_block(seasons):
    out = {}
    Ls = identical(ALL, seasons, MODELS).join(gflag, on="game_id", how="left")
    for f in ("change", "newc", "backup", "late"):
        S_ = Ls.filter(pl.col(f))
        o = {"n_games": S_["game_id"].n_unique()}
        for a, b in (("QL", "v2.2"), ("v1.0+QL", "v1.0"), ("QL-B27", "v2.2"), ("QL-B1", "v2.2")):
            if S_.height:
                c = compare(S_, a, b)
                o[f"{a}_vs_{b}"] = {k: c[k] for k in ("mse_a", "mse_b", "diff_se", "ci95_se", "n_games")}
        # mean (actual - model) margin for the flagged side (positive: the flagged side did better than predicted)
        fs_ = side.filter(pl.col(f)).select("game_id", "team")
        for m in ("v1.0", "v2.2", "QL"):
            Pm = ALL.filter((pl.col("model") == m) & pl.col("season").is_in(seasons)).join(fs_, on="game_id")
            Pm = Pm.with_columns(r=(pl.col("margin") - pl.col("pred_margin")) * pl.when(pl.col("team") == pl.col("home_id")).then(1.0).otherwise(-1.0))
            n = Pm.height
            o[f"resid_{m}"] = {"n_sides": n, "mean": float(Pm["r"].mean()) if n else None,
                               "se": float(Pm["r"].std() / np.sqrt(n)) if n > 1 else None}
        out[f] = o
    return out


res["subsets_2019_24"] = subset_block(FOLDS)
res["subsets_2025_seen"] = subset_block([2025])
res["subsets_2026_seen"] = subset_block([2026])


# ---------------------------------------------------------------- "inherited production" check
def inherit(seasons):
    out = {}
    for m in ("v1.0", "v2.2", "QL"):
        Pm = ALL.filter((pl.col("model") == m) & pl.col("season").is_in(seasons))
        rows = pl.concat([Pm.select("game_id", team="home_id", r=pl.col("home_score") - pl.col("pred_home")),
                          Pm.select("game_id", team="away_id", r=pl.col("away_score") - pl.col("pred_away"))])
        rows = rows.join(side.select("game_id", "team", "change", "newc", pl.col("cur|qb_delta").alias("delta"), "qbs_share"), on=["game_id", "team"])
        o = {}
        for lab, sub in (("qb_change", rows.filter(pl.col("change"))), ("no_change", rows.filter(~pl.col("change"))),
                         ("change_newcomer", rows.filter(pl.col("change") & pl.col("newc")))):
            x, y = sub["delta"].to_numpy(), sub["r"].to_numpy()
            if len(x) < 10:
                continue
            xc = x - x.mean()
            b = float((xc * (y - y.mean())).sum() / (xc ** 2).sum())
            e = y - y.mean() - b * xc
            o[lab] = {"n": len(x), "slope_pts_per_1epa": b, "se": float(np.sqrt((e ** 2).sum() / (len(x) - 2) / (xc ** 2).sum())),
                      "mean_resid": float(y.mean()), "mean_delta": float(x.mean())}
        out[m] = o
    return out


res["inherited_2019_24"] = inherit(FOLDS)
res["inherited_2019_25"] = inherit(FOLDS + [2025])


# ---------------------------------------------------------------- gap-vs-result slopes (untimed lines)
def slopes(df):
    out = {}
    for m in ("v1.0", "v2.2", "QL", "v1.0+QL"):
        d = df.filter((pl.col("model") == m) & pl.col("market_available")).with_columns(
            gap=pl.col("pred_margin") + pl.col("home_spread"), res=pl.col("margin") + pl.col("home_spread"), big=pl.col("home_spread").abs() >= 7)
        o = {}
        for lab, sub in (("all", d), ("spread_lt7", d.filter(~pl.col("big"))), ("spread_ge7", d.filter(pl.col("big")))):
            x, y = sub["gap"].to_numpy(), sub["res"].to_numpy()
            xc = x - x.mean()
            b = float((xc * (y - y.mean())).sum() / (xc ** 2).sum())
            e = y - y.mean() - b * xc
            o[lab] = {"n": len(x), "slope": b, "se": float(np.sqrt((e ** 2).sum() / (len(x) - 2) / (xc ** 2).sum()))}
        out[m] = o
    return out


res["gap_slopes_2019_25"] = slopes(ALL.filter(pl.col("season").is_between(2019, 2025)))

# ---------------------------------------------------------------- leakage test (20 seeded targets)
rng = np.random.default_rng(SEED)
cand = T.join(games.select("game_id", "kickoff_utc", "status"), on="game_id").filter((pl.col("season") >= 2017) & (pl.col("status") == "final"))
pick = cand[sorted(rng.choice(cand.height, 20, replace=False).tolist())]
pbp = B.load_pbp()
ko = games.select("game_id", "kickoff_utc")
leak = []
for r in pick.iter_rows(named=True):
    k = r["kickoff_utc"]
    keep = ko.filter(pl.col("kickoff_utc") < k)["game_id"]
    c2 = {"games": games, "tg": ctx["tg"].filter(pl.col("game_id").is_in(keep)), "qbg": ctx["qbg"].filter(pl.col("game_id").is_in(keep))}
    p2 = pbp.filter(pl.col("game_id").is_in(keep))
    qt = B.qb_game_table(p2, games, c2["qbg"], B.qb_positions())
    c2["qt"] = B.add_opp_adjust(qt, B.OppDefence(c2["tg"]))
    c2["bucket"] = ctx["bucket"]
    t1 = T.filter((pl.col("game_id") == r["game_id"]) & (pl.col("team") == r["team"]))
    a = B.build(c2, [B.Cfg(runs=True, opp=True, ped=True)], t1)
    b = TI.filter((pl.col("game_id") == r["game_id"]) & (pl.col("team") == r["team"]))
    cols = [c for c in a.columns if c not in ("game_id", "team", "prev_starter")]
    leak.append({"game_id": r["game_id"], "team": r["team"], "max_abs_diff": max(abs(float(a[c][0]) - float(b[c][0])) for c in cols)})
res["leakage"] = {"n": len(leak), "max_abs_diff": max(x["max_abs_diff"] for x in leak), "targets": leak}
log("leakage", res["leakage"]["max_abs_diff"])

out = RD / f"qb_layer_v2_3_evaluation_{stamp}.json"
out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
c = res["primary"]
print(f"PRIMARY QL vs v2.2 n={c['n_games']} MSE {c['mse_b']:.3f}->{c['mse_a']:.3f} diff {c['diff_se']:+.3f} "
      f"[{c['ci95_se'][0]:+.3f},{c['ci95_se'][1]:+.3f}] better {c['seasons_better']}/6 dev {c['dev_mse_b']:.2f}->{c['dev_mse_a']:.2f}")
for a, c in res["arms_vs_v2.2"].items():
    print(f"{a:12s} vs v2.2 MSE {c['mse_a']:.3f} diff {c['diff_se']:+.3f} [{c['ci95_se'][0]:+.3f},{c['ci95_se'][1]:+.3f}] "
          f"better {c['seasons_better']}/6 dev {c['dev_mse_a']:.2f} total {c['diff_total_se']:+.2f}")
for a, c in res["arms_vs_v1.0"].items():
    print(f"{a:12s} vs v1.0 diff {c['diff_se']:+.3f} [{c['ci95_se'][0]:+.3f},{c['ci95_se'][1]:+.3f}] better {c['seasons_better']}/6")
print("wrote", out.name)
