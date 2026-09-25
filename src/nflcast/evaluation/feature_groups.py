"""Separate chronological evaluation of candidate feature groups before any production promotion.

PRE-SPECIFIED PROMOTION RULE (fixed before results were seen, 2026-09-25):
  A feature group is promoted into the production (combined) model only if, for the combined model at the final
  horizon, adding the group
    (1) reduces the group's target loss in the DEV seasons with a 95% season-week block-bootstrap interval entirely
        below zero, AND
    (2) also reduces it (mean difference < 0) in the TUNE seasons.
  Target loss: squared error of the total for weather; squared error of margin plus squared error of total for
  non-QB injuries. The football-only model is evaluated the same way and reported, but it is the fallback, not the
  headline model. The locked 2025 season is NOT used for these evaluations.
  Weather has an extra requirement: its historical inputs are retrospective (stitched short-lead forecasts, not what
  was knowable at the forecast cutoff), so even a pass only makes it a "candidate" until strictly as-of prospective
  snapshots confirm it.
Both arms of every comparison are trained on identical games and seasons.
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl

from nflcast.config import PROCESSED_DIR, REPORTS_DIR, settings, utc_now, utc_stamp
from nflcast.evaluation import backtest as BT
from nflcast.evaluation.metrics import block_bootstrap_diff, per_game_losses, point_metrics

RULE = __doc__.split("PRE-SPECIFIED PROMOTION RULE")[1].split("Both arms")[0].strip()


def _load(horizon: str = "final") -> pl.DataFrame:
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    feats = pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet")
    market = pl.read_parquet(PROCESSED_DIR / "market_asof.parquet")
    return BT.assemble(games, feats, market).filter(pl.col("horizon") == horizon)


def _compare(preds: pl.DataFrame, base: str, cand: str, losses: list[str], tune: list[int], dev: list[int], reps: int, seed: int) -> dict:
    L = per_game_losses(preds).with_columns(target=sum(pl.col(l) for l in losses))
    out = {}
    for period, seasons in (("tune", tune), ("dev", dev)):
        a = L.filter((pl.col("model") == cand) & pl.col("season").is_in(seasons))
        b = L.filter((pl.col("model") == base) & pl.col("season").is_in(seasons))
        if a.height == 0:
            continue
        out[period] = {"paired_target": block_bootstrap_diff(a, b, "target", reps, seed),
                       "metrics_candidate": point_metrics(a), "metrics_base": point_metrics(b)}
    return out


def _decision(combined: dict, retrospective: bool) -> str:
    dev, tune = combined.get("dev"), combined.get("tune")
    if not dev or not tune:
        return "not evaluable"
    passed = dev["paired_target"]["ci95"][1] < 0 and tune["paired_target"]["mean_diff"] < 0
    if not passed:
        return "not promoted (rule not met)"
    return "candidate only (retrospective inputs; needs prospective confirmation)" if retrospective else "promote"


def evaluate_injuries(reps: int, seed: int) -> dict:
    v = settings()["validation"]
    tune, dev = list(v["tune_folds"]), list(v["dev_folds"])
    data = _load("final")
    preds, _ = BT.run(data, tune + dev, ["final"],
                      specs=[("B_qb", "core_qb", ("final",)), ("B_qb_inj", "core_qb_inj", ("final",))],
                      combined_specs=[("C_qb", "core_qb"), ("C_qb_inj", "core_qb_inj")])
    comb = _compare(preds, "C_qb", "C_qb_inj", ["se_margin", "se_total"], tune, dev, reps, seed)
    foot = _compare(preds, "B_qb", "B_qb_inj", ["se_margin", "se_total"], tune, dev, reps, seed)
    return {"group": "non-QB injuries (final weekly report; expected lost snap share by unit)", "horizon": "final",
            "inputs": "final weekly injury report (strictly available before the final horizon)", "retrospective": False,
            "tune": tune, "dev": dev, "combined": comb, "football_only": foot, "decision": _decision(comb, False),
            "early_horizon": "not evaluable: mid-week report versions are not retained historically (now being collected)"}


def evaluate_weather(reps: int, seed: int) -> dict:
    from nflcast.features import weather as W
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    hist = W.weather_features(W.historical_kickoff_weather(games, PROCESSED_DIR / "weather_historical_forecast.parquet"))
    data = _load("final").join(hist.select(["game_id"] + W.WX_FEATURES), on="game_id", how="inner")
    tune, dev = [2021], [2022, 2023, 2024]
    preds, _ = BT.run(data, tune + dev, ["final"], train_start=2019,
                      specs=[("B_qb", "core_qb", ("final",)), ("B_qb_wx", "core_qb_wx", ("final",))],
                      combined_specs=[("C_qb", "core_qb"), ("C_qb_wx", "core_qb_wx")])
    comb = _compare(preds, "C_qb", "C_qb_wx", ["se_total"], tune, dev, reps, seed)
    foot = _compare(preds, "B_qb", "B_qb_wx", ["se_total"], tune, dev, reps, seed)
    return {"group": "weather (exposure-weighted wind, gusts, cold, precipitation)", "horizon": "final",
            "inputs": "RETROSPECTIVE: Open-Meteo Historical Forecast API (stitched short-lead forecasts), 2019+",
            "retrospective": True, "games_with_weather": data["game_id"].n_unique(), "train_start": 2019,
            "tune": tune, "dev": dev, "combined": comb, "football_only": foot, "decision": _decision(comb, True)}


def to_markdown(results: list[dict]) -> str:
    L = ["# Feature-group evaluations", "", f"Generated {utc_now().isoformat()}.", "", "## Pre-specified promotion rule", "", RULE, ""]
    for r in results:
        L += [f"## {r['group']}", "", f"Inputs: {r['inputs']}. Horizon: {r['horizon']}. Tune seasons {r['tune']}, dev seasons {r['dev']}.",
              "", f"**Decision: {r['decision']}**", ""]
        if r.get("early_horizon"):
            L += [f"Early horizon: {r['early_horizon']}.", ""]
        L += ["| model | period | n | loss diff (cand − base) | 95% CI | margin RMSE base → cand | total RMSE base → cand |",
              "|---|---|---|---|---|---|---|"]
        for arm in ("combined", "football_only"):
            for period, x in r[arm].items():
                p, mb, mc = x["paired_target"], x["metrics_base"], x["metrics_candidate"]
                L.append(f"| {arm} | {period} | {p['n_games']} | {p['mean_diff']:+.3f} | [{p['ci95'][0]:+.3f}, {p['ci95'][1]:+.3f}] | "
                         f"{mb['margin_rmse']:.3f} → {mc['margin_rmse']:.3f} | {mb['total_rmse']:.3f} → {mc['total_rmse']:.3f} |")
        L.append("")
    return "\n".join(L)


def run() -> list[dict]:
    v = settings()["validation"]
    res = [evaluate_injuries(v["bootstrap_reps"], v["seed"]), evaluate_weather(v["bootstrap_reps"], v["seed"])]
    d = REPORTS_DIR / "feature_groups"
    d.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    (d / f"feature_groups_{stamp}.json").write_text(json.dumps({"rule": RULE, "results": res}, indent=1, default=str), encoding="utf-8")
    md = to_markdown(res)
    (d / f"feature_groups_{stamp}.md").write_text(md, encoding="utf-8")
    (d / "LATEST.md").write_text(md, encoding="utf-8")
    print(md)
    return res
