"""Score prospectively published releases against final results.

For each completed game, the scored forecast is the specific frozen release version that was
generated BEFORE the relevant cutoff (never a later model run):
  * final_pregame: the latest release generated before kickoff
  * early: the latest release generated at least `horizons.early` hours before kickoff
One row per (game, horizon type), so repeated versions never inflate the sample.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import polars as pl

from nflcast.config import RELEASES_DIR, REPORTS_DIR, settings
from nflcast.data import sources as S
from nflcast.data.games import build_games


def load_release_entries() -> pl.DataFrame:
    rows = []
    for f in sorted(RELEASES_DIR.rglob("rel_*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("schema_version", 1) < 2:
            continue  # milestone-2 baseline releases have no probabilities; kept on disk, not scored
        for g in r["games"]:
            fc = g["forecast"]
            rows.append({
                "run_id": r["run_id"], "generated_at": datetime.fromisoformat(r["generated_at_utc"]),
                "game_id": g["game_id"], "kickoff": datetime.fromisoformat(g["kickoff_utc"]), "status": g["status"],
                "primary_model": g["primary_model"], "pred_home": fc["home_pts"], "pred_away": fc["away_pts"],
                "pred_margin": fc["margin"], "pred_total": fc["total"], "p_home": fc["p_home"], "p_away": fc["p_away"],
                "p_tie": fc["p_tie"], "m80_lo": fc["intervals"]["margin_80"][0], "m80_hi": fc["intervals"]["margin_80"][1],
                "t80_lo": fc["intervals"]["total_80"][0], "t80_hi": fc["intervals"]["total_80"][1],
                "mkt_margin": g["market_only"]["margin"] if g.get("market_only") else None,
                "mkt_total": g["market_only"]["total"] if g.get("market_only") else None,
                "fb_margin": g["football_only"]["margin"], "fb_total": g["football_only"]["total"],
            })
    return pl.DataFrame(rows) if rows else pl.DataFrame()


def frozen_versions(entries: pl.DataFrame) -> pl.DataFrame:
    early_h = settings()["horizons"]["early"]
    pre = entries.filter(pl.col("generated_at") < pl.col("kickoff"))
    fin = pre.sort("generated_at").group_by("game_id").last().with_columns(horizon_type=pl.lit("final_pregame"))
    ear = (pre.filter(pl.col("generated_at") <= pl.col("kickoff") - timedelta(hours=early_h))
           .sort("generated_at").group_by("game_id").last().with_columns(horizon_type=pl.lit("early")))
    return pl.concat([fin, ear])


def score() -> dict:
    entries = load_release_entries()
    out_dir = REPORTS_DIR / "prospective"
    out_dir.mkdir(parents=True, exist_ok=True)
    if entries.height == 0:
        summary = {"n_scored": 0, "note": "no schema-v2 releases yet"}
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        return summary
    games = build_games(S.fetch("schedules")).filter(pl.col("status") == "final").select(
        "game_id", "home_score", "away_score", "margin", "total_points")
    fz = frozen_versions(entries).join(games, on="game_id", how="inner")
    ev = fz.with_columns(
        ae_margin=(pl.col("pred_margin") - pl.col("margin")).abs(),
        ae_total=(pl.col("pred_total") - pl.col("total_points")).abs(),
        ae_margin_market=(pl.col("mkt_margin") - pl.col("margin")).abs(),
        ae_total_market=(pl.col("mkt_total") - pl.col("total_points")).abs(),
        ae_margin_football=(pl.col("fb_margin") - pl.col("margin")).abs(),
        winner_correct=pl.when(pl.col("margin") != 0).then((pl.col("pred_margin") > 0) == (pl.col("margin") > 0)),
        in_m80=(pl.col("margin") >= pl.col("m80_lo")) & (pl.col("margin") <= pl.col("m80_hi")),
        in_t80=(pl.col("total_points") >= pl.col("t80_lo")) & (pl.col("total_points") <= pl.col("t80_hi")),
        p_obs=pl.when(pl.col("margin") > 0).then(pl.col("p_home")).when(pl.col("margin") < 0).then(pl.col("p_away")).otherwise(pl.col("p_tie")),
    ).with_columns(log_loss=-pl.col("p_obs").clip(1e-12, 1).log())
    ev.write_parquet(out_dir / "evaluations.parquet")
    summary = {"n_scored": ev.height, "by_horizon": ev.group_by("horizon_type").agg(
        n=pl.len(), margin_mae=pl.col("ae_margin").mean(), total_mae=pl.col("ae_total").mean(),
        market_margin_mae=pl.col("ae_margin_market").mean(), market_total_mae=pl.col("ae_total_market").mean(),
        football_margin_mae=pl.col("ae_margin_football").mean(), winner_acc=pl.col("winner_correct").mean(),
        log_loss=pl.col("log_loss").mean(), cover_m80=pl.col("in_m80").mean(), cover_t80=pl.col("in_t80").mean(),
    ).to_dicts()}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(f"[score] scored {ev.height} frozen forecasts")
    return summary
