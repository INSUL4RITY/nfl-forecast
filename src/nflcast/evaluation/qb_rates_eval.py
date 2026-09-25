"""Chronological evaluation of QB start-probability estimators (training data only).

Target: did the depth-chart QB1 START the game (not "play", not "be active"). For each test season S the
estimator is fitted on seasons < S only and scored on season S. Candidate estimators:
  status_beta11      P(start | final-report status), Beta(1,1) smoothing            (previous production)
  status_jeffreys    same with Jeffreys Beta(0.5,0.5)
  status_x_practice  P(start | status, final practice participation), shrunk toward the status rate with
                     pseudo-count m chosen by nested chronological validation inside the training seasons
Scored on all QB1 team-games and on the Questionable/Doubtful subset (the uncertain cases).
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl
from scipy.stats import beta as beta_dist

from nflcast.config import REPORTS_DIR, utc_now

M_GRID = (0.0, 2.0, 5.0, 10.0, 20.0, 50.0, 1e9)


def practice_bucket(expr: pl.Expr) -> pl.Expr:
    return (pl.when(expr.str.contains("(?i)did not|out \\(")).then(pl.lit("DNP"))
            .when(expr.str.contains("(?i)limited")).then(pl.lit("Limited"))
            .when(expr.str.contains("(?i)full")).then(pl.lit("Full"))
            .otherwise(pl.lit("NoPractice")))


def interval(k: int, n: int, a: float = 0.5, b: float = 0.5, level: float = 0.9) -> tuple[float, float]:
    lo, hi = beta_dist.ppf([(1 - level) / 2, 1 - (1 - level) / 2], k + a, n - k + b)
    return float(lo), float(hi)


def fit_status(train: pl.DataFrame, a: float, b: float) -> dict:
    out = {}
    for (st,), g in train.group_by(["qb1_status"]):
        k, n = int(g["started"].sum()), g.height
        out[st] = (k + a) / (n + a + b)
    k, n = int(train["started"].sum()), train.height
    out["__pooled__"] = (k + a) / (n + a + b)
    return out


def fit_status_practice(train: pl.DataFrame, m: float) -> dict:
    base = fit_status(train, 0.5, 0.5)
    out = {"__status__": base}
    for (st, pb), g in train.group_by(["qb1_status", "qb1_practice"]):
        k, n = int(g["started"].sum()), g.height
        prior = base.get(st, base["__pooled__"])
        out[(st, pb)] = prior if m >= 1e8 else (k + m * prior) / (n + m) if n + m > 0 else prior
    return out


def predict_status(model: dict, df: pl.DataFrame) -> np.ndarray:
    return np.array([model.get(s, model["__pooled__"]) for s in df["qb1_status"].to_list()])


def predict_practice(model: dict, df: pl.DataFrame) -> np.ndarray:
    base = model["__status__"]
    return np.array([model.get((s, p), base.get(s, base["__pooled__"])) for s, p in zip(df["qb1_status"], df["qb1_practice"])])


def _scores(p: np.ndarray, y: np.ndarray) -> dict:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return {"n": int(len(y)), "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "brier": float(np.mean((p - y) ** 2)), "mean_pred": float(p.mean()), "obs_rate": float(y.mean())}


def choose_m(train: pl.DataFrame) -> float:
    """Nested chronological choice of the shrinkage pseudo-count using only the training seasons."""
    seasons = sorted(train["season"].unique().to_list())
    if len(seasons) < 3:
        return 10.0
    best, best_ll = 10.0, np.inf
    for m in M_GRID:
        ll = []
        for s in seasons[2:]:
            tr, te = train.filter(pl.col("season") < s), train.filter((pl.col("season") == s)
                                                                      & pl.col("qb1_status").is_in(["Questionable", "Doubtful"]))
            if te.height == 0:
                continue
            ll.append(_scores(predict_practice(fit_status_practice(tr, m), te), te["started"].to_numpy())["log_loss"] * te.height)
        tot = float(np.sum(ll))
        if tot < best_ll:
            best, best_ll = m, tot
    return best


def evaluate(tw: pl.DataFrame, test_seasons: list[int]) -> dict:
    rows, chosen = [], {}
    for S in test_seasons:
        tr, te = tw.filter(pl.col("season") < S), tw.filter(pl.col("season") == S)
        if te.height == 0 or tr.height == 0:
            continue
        m = choose_m(tr)
        chosen[S] = m
        preds = {"status_beta11": predict_status(fit_status(tr, 1, 1), te),
                 "status_jeffreys": predict_status(fit_status(tr, 0.5, 0.5), te),
                 "status_x_practice": predict_practice(fit_status_practice(tr, m), te)}
        for name, p in preds.items():
            rows.append(te.select("season", "qb1_status", "started").with_columns(method=pl.lit(name), p=pl.Series(p)))
    pr = pl.concat(rows)
    res = {"generated_at": utc_now().isoformat(), "test_seasons": test_seasons, "chosen_m_by_season": chosen, "overall": [], "uncertain": [],
           "by_status": [], "paired": []}
    # paired log-loss difference vs the previous production estimator, bootstrap over test cases
    rng = np.random.default_rng(20260925)
    base = pr.filter(pl.col("method") == "status_beta11")
    for name in ("status_jeffreys", "status_x_practice"):
        alt = pr.filter(pl.col("method") == name)
        for subset, mask in (("uncertain", base["qb1_status"].is_in(["Questionable", "Doubtful"]).to_numpy()),
                             ("overall", np.ones(base.height, bool))):
            y = base["started"].to_numpy()[mask]
            pa, pb = np.clip(alt["p"].to_numpy()[mask], 1e-4, 1 - 1e-4), np.clip(base["p"].to_numpy()[mask], 1e-4, 1 - 1e-4)
            d = -(y * np.log(pa) + (1 - y) * np.log(1 - pa)) + (y * np.log(pb) + (1 - y) * np.log(1 - pb))
            boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
            res["paired"].append({"method": name, "vs": "status_beta11", "subset": subset, "n": int(len(d)),
                                  "mean_logloss_diff": float(d.mean()),
                                  "ci95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))]})
    for (name,), g in pr.group_by(["method"], maintain_order=True):
        res["overall"].append({"method": name, **_scores(g["p"].to_numpy(), g["started"].to_numpy())})
        u = g.filter(pl.col("qb1_status").is_in(["Questionable", "Doubtful"]))
        res["uncertain"].append({"method": name, **_scores(u["p"].to_numpy(), u["started"].to_numpy())})
        for (st,), gs in g.group_by(["qb1_status"]):
            res["by_status"].append({"method": name, "status": st, **_scores(gs["p"].to_numpy(), gs["started"].to_numpy())})
    return res


def audit_table(tw: pl.DataFrame) -> list[dict]:
    """What the Questionable/Doubtful cases measure: started vs played vs inactive, by practice status."""
    out = []
    for st in ("Questionable", "Doubtful"):
        d = tw.filter(pl.col("qb1_status") == st)
        for (pb,), g in d.group_by(["qb1_practice"]):
            k, n = int(g["started"].sum()), g.height
            lo, hi = interval(k, n)
            out.append({"status": st, "practice": pb, "n": n, "started": k,
                        "played_not_started": int(((g["played_snap"] == 1) & (g["started"] == 0)).sum()) if "played_snap" in g.columns else None,
                        "declared_inactive": int((g["roster_status"] == "INA").sum()) if "roster_status" in g.columns else None,
                        "p_start_jeffreys": (k + 0.5) / (n + 1), "ci90": [lo, hi]})
    return sorted(out, key=lambda r: (r["status"], -r["n"]))


def build_audit_table(seasons: list[int]) -> pl.DataFrame:
    """Depth-chart QB1 team-games with final status, final practice, started / played (snaps) / declared inactive."""
    from nflcast.config import PROCESSED_DIR
    from nflcast.data import sources as S
    from nflcast.data.games import franchise
    from nflcast.features import personnel as P
    from nflcast.features import qb_availability as Q
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    qbg = pl.read_parquet(PROCESSED_DIR / "qb_games.parquet")
    tw = Q.build_history_team_weeks(games, qbg, Q.weekly_depth_qbs(seasons), P.injury_player_weeks(seasons, games),
                                    Q.injury_practice(seasons))
    ids = S.fetch("players").select("gsis_id", pl.col("pfr_id").alias("pfr_player_id")).drop_nulls().unique("gsis_id")
    snaps = pl.concat([S.fetch("snap_counts", s).select("game_id", "pfr_player_id", "offense_snaps") for s in seasons])
    snaps = snaps.join(ids, on="pfr_player_id").select("game_id", pl.col("gsis_id").alias("qb1"), "offense_snaps")
    tw = tw.join(snaps, on=["game_id", "qb1"], how="left").with_columns(
        played_snap=(pl.col("offense_snaps").fill_null(0) > 0).cast(pl.Int32))
    ros = pl.concat([S.fetch("rosters_weekly", s).select(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32),
                                                         franchise(pl.col("team")).alias("team"), pl.col("gsis_id").alias("qb1"),
                                                         pl.col("status").alias("roster_status")) for s in seasons])
    return tw.join(ros.unique(["season", "week", "team", "qb1"], keep="last"), on=["season", "week", "team", "qb1"], how="left")


def run(seasons: list[int] | None = None, test_seasons: list[int] | None = None) -> dict:
    seasons = seasons or list(range(2016, 2025))
    tw = build_audit_table(seasons)
    res = evaluate(tw, test_seasons or list(range(2019, 2025)))
    audit = audit_table(tw)
    write_report(res, audit)
    print(f"[qb-rates] wrote {REPORTS_DIR / 'qb_availability' / 'evaluation.md'}")
    return res


def write_report(res: dict, audit: list[dict]) -> None:
    d = REPORTS_DIR / "qb_availability"
    d.mkdir(parents=True, exist_ok=True)
    (d / "evaluation.json").write_text(json.dumps({"evaluation": res, "audit": audit}, indent=1), encoding="utf-8")
    L = ["# QB start-probability audit and evaluation", "",
         f"Generated {res['generated_at']}. Target = the depth-chart QB1 **started** (weekly depth charts 2016-2024).",
         "Each test season is predicted from earlier seasons only.", "",
         "## What the Questionable / Doubtful cases measure", "",
         "| status | final practice | n | started | played, not started | declared inactive | P(start) Jeffreys | 90% interval |",
         "|---|---|---|---|---|---|---|---|"]
    for a in audit:
        L.append(f"| {a['status']} | {a['practice']} | {a['n']} | {a['started']} | {a['played_not_started']} | {a['declared_inactive']} | "
                 f"{a['p_start_jeffreys']:.2f} | {a['ci90'][0]:.2f}-{a['ci90'][1]:.2f} |")
    L += ["", "## Chronological evaluation (test seasons " + ", ".join(map(str, res["test_seasons"])) + ")", "",
          "| method | subset | n | log loss | Brier | mean predicted | observed |", "|---|---|---|---|---|---|---|"]
    for subset in ("uncertain", "overall"):
        for r in res[subset]:
            L.append(f"| {r['method']} | {'Questionable+Doubtful' if subset == 'uncertain' else 'all QB1 games'} | {r['n']} | "
                     f"{r['log_loss']:.4f} | {r['brier']:.4f} | {r['mean_pred']:.3f} | {r['obs_rate']:.3f} |")
    L += ["", "Paired log-loss difference vs the previous estimator (negative = better; bootstrap over test cases):", "",
          "| method | subset | n | mean diff | 95% CI |", "|---|---|---|---|---|"]
    for r in res["paired"]:
        L.append(f"| {r['method']} | {r['subset']} | {r['n']} | {r['mean_logloss_diff']:+.4f} | [{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}] |")
    L += ["", f"Shrinkage pseudo-count m chosen per test season (nested, training seasons only): {res['chosen_m_by_season']}",
          "", "Note: all estimators over-predict starts for Questionable/Doubtful QBs in these test seasons (mean predicted vs observed "
          "above): the start rate for listed QBs has drifted down in recent seasons (e.g. 9/27 Questionable QB1s started in 2024). "
          "This is reported, not corrected; a recency-weighted estimator is a candidate for future evaluation."]
    (d / "evaluation.md").write_text("\n".join(L), encoding="utf-8")
