"""Score prospectively generated releases against final results.

For each completed game, the scored forecast is the specific frozen version that was generated BEFORE the
relevant cutoff and passed validation (never a later model run, never an invalid version):
  * final_pregame: the latest valid version generated before kickoff
  * early: the latest valid version generated at least `horizons.early` hours before kickoff
One row per (game, horizon type), so repeated versions never inflate the sample.
Each scored row carries a verification label from independent publication evidence
(predict/publication.py). Summaries are reported for all generated-pregame forecasts AND separately for
the publicly verifiable subset.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import polars as pl

from nflcast.config import RELEASES_DIR, REPORTS_DIR, release_paths, settings
from nflcast.data import sources as S
from nflcast.data.games import build_games
from nflcast.predict import publication as PUB
from nflcast.predict.validation import entry_is_valid


def load_release_entries() -> pl.DataFrame:
    ev = PUB.load_evidence()
    rows = []
    for f in release_paths():
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("schema_version", 1) < 2:
            continue  # milestone-2 baseline releases have no probabilities; kept on disk, not scored
        pub = PUB.public_time(r["run_id"], ev)
        for g in r["games"]:
            fc = g.get("forecast") or {}
            iv = fc.get("intervals", {})
            rows.append({
                "run_id": r["run_id"], "generated_at": datetime.fromisoformat(r["generated_at_utc"]),
                "public_at": pub, "game_id": g["game_id"], "kickoff": datetime.fromisoformat(g["kickoff_utc"]),
                "status": g["status"], "valid": entry_is_valid(g), "primary_model": g.get("primary_model"),
                "pred_home": fc.get("home_pts"), "pred_away": fc.get("away_pts"), "pred_margin": fc.get("margin"),
                "pred_total": fc.get("total"), "p_home": fc.get("p_home"), "p_away": fc.get("p_away"), "p_tie": fc.get("p_tie"),
                "m80_lo": (iv.get("margin_80") or [None, None])[0], "m80_hi": (iv.get("margin_80") or [None, None])[1],
                "t80_lo": (iv.get("total_80") or [None, None])[0], "t80_hi": (iv.get("total_80") or [None, None])[1],
                "mkt_margin": g["market_only"]["margin"] if g.get("market_only") else None,
                "mkt_total": g["market_only"]["total"] if g.get("market_only") else None,
                "fb_margin": (g.get("football_only") or {}).get("margin"), "fb_total": (g.get("football_only") or {}).get("total"),
            })
    if not rows:
        return pl.DataFrame()
    df = pl.DataFrame(rows, infer_schema_length=None)
    return df.with_columns(pl.col("public_at").cast(pl.Datetime("us", "UTC")))


def frozen_versions(entries: pl.DataFrame) -> pl.DataFrame:
    early_h = settings()["horizons"]["early"]
    ok = entries.filter(pl.col("valid") & (pl.col("generated_at") < pl.col("kickoff")))
    fin = ok.sort("generated_at").group_by("game_id").last().with_columns(horizon_type=pl.lit("final_pregame"))
    ear = (ok.filter(pl.col("generated_at") <= pl.col("kickoff") - timedelta(hours=early_h))
           .sort("generated_at").group_by("game_id").last().with_columns(horizon_type=pl.lit("early")))
    out = pl.concat([fin, ear], how="diagonal_relaxed")
    return out.with_columns(verification=(
        pl.when(pl.col("public_at").is_null()).then(pl.lit("generated_pregame_not_yet_evidenced_public"))
        .when(pl.col("public_at") < pl.col("kickoff")).then(pl.lit("publicly_verifiable_pregame"))
        .otherwise(pl.lit("generated_pregame_published_after_kickoff"))))


def _summary(ev: pl.DataFrame) -> list[dict]:
    return ev.group_by("horizon_type").agg(
        n=pl.len(), margin_mae=pl.col("ae_margin").mean(), total_mae=pl.col("ae_total").mean(),
        market_margin_mae=pl.col("ae_margin_market").mean(), market_total_mae=pl.col("ae_total_market").mean(),
        football_margin_mae=pl.col("ae_margin_football").mean(), winner_acc=pl.col("winner_correct").mean(),
        log_loss=pl.col("log_loss").mean(), cover_m80=pl.col("in_m80").mean(), cover_t80=pl.col("in_t80").mean(),
    ).sort("horizon_type").to_dicts()


def score() -> dict:
    entries = load_release_entries()
    out_dir = REPORTS_DIR / "prospective"
    out_dir.mkdir(parents=True, exist_ok=True)
    if entries.height == 0:
        summary = {"n_scored": 0, "note": "no schema-v2+ releases yet"}
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
    pv = ev.filter(pl.col("verification") == "publicly_verifiable_pregame")
    summary = {"n_scored": ev.height, "by_horizon": _summary(ev) if ev.height else [],
               "n_publicly_verifiable": pv.height, "by_horizon_publicly_verifiable": _summary(pv) if pv.height else [],
               "verification_counts": ev.group_by("verification").len().sort("verification").to_dicts() if ev.height else []}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(f"[score] scored {ev.height} frozen forecasts ({pv.height} publicly verifiable)")
    return summary
