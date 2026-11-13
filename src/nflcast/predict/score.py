"""Score prospectively generated releases against final results.

For each completed game, the scored forecast is the specific frozen version that was generated BEFORE the
relevant cutoff and passed validation (never a later model run, never an invalid version):
  * final_pregame: the latest valid version generated before kickoff
  * early: the latest valid version generated at least `horizons.early` hours before kickoff
One row per (game, horizon type), so repeated versions never inflate the sample.
Each scored row carries a verification label from independent publication evidence
(predict/publication.py). Summaries are reported for all generated-pregame forecasts AND separately for
the publicly verifiable subset.

Scores per forecast (audit 2026-11-13 added Brier, the stats-only line and 95% coverage):
  * headline forecast (combined market-adjusted model, or the football-only fallback): margin/total error, winner,
    log loss, 3-class Brier score, 80% and 95% interval coverage for margin and total;
  * stats-only line (`football_only`; the public "Model line" and win probability since week 7): the same
    probability and interval scores, so the probability shown on the site is scored too.
Reporting only: nothing here changes a forecast, a pick or a grade.
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


def _probs(prefix: str, fc: dict | None) -> dict:
    """Probabilities and 80%/95% interval bounds of one forecast block, as flat columns with `prefix`."""
    fc = fc or {}
    iv = fc.get("intervals") or {}
    out = {f"{prefix}p_home": fc.get("p_home"), f"{prefix}p_away": fc.get("p_away"), f"{prefix}p_tie": fc.get("p_tie")}
    for tgt in ("margin", "total"):
        for lv in (80, 95):
            lo, hi = iv.get(f"{tgt}_{lv}") or [None, None]
            out[f"{prefix}{tgt[0]}{lv}_lo"], out[f"{prefix}{tgt[0]}{lv}_hi"] = lo, hi
    return out


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
            rows.append({
                "run_id": r["run_id"], "generated_at": datetime.fromisoformat(r["generated_at_utc"]),
                "public_at": pub, "game_id": g["game_id"], "kickoff": datetime.fromisoformat(g["kickoff_utc"]),
                "status": g["status"], "valid": entry_is_valid(g), "primary_model": g.get("primary_model"),
                "pred_home": fc.get("home_pts"), "pred_away": fc.get("away_pts"), "pred_margin": fc.get("margin"),
                "pred_total": fc.get("total"), **_probs("", fc), **_probs("fb_", g.get("football_only")),
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
    cov = [pl.col(f"{pre}in_{t}{lv}").mean().alias(f"{name}cover_{t}{lv}")
           for pre, name in (("", ""), ("fb_", "stats_only_")) for t in ("m", "t") for lv in (80, 95)]
    return ev.group_by("horizon_type").agg(
        n=pl.len(), margin_mae=pl.col("ae_margin").mean(), total_mae=pl.col("ae_total").mean(),
        market_margin_mae=pl.col("ae_margin_market").mean(), market_total_mae=pl.col("ae_total_market").mean(),
        football_margin_mae=pl.col("ae_margin_football").mean(), winner_acc=pl.col("winner_correct").mean(),
        log_loss=pl.col("log_loss").mean(), brier=pl.col("brier").mean(),
        n_stats_only=pl.col("fb_log_loss").count(), stats_only_log_loss=pl.col("fb_log_loss").mean(),
        stats_only_brier=pl.col("fb_brier").mean(), *cov,
    ).sort("horizon_type").to_dicts()


def evaluate(fz: pl.DataFrame) -> pl.DataFrame:
    """Per-forecast scores for frozen versions joined to final results (margin, total_points)."""
    m, t = pl.col("margin"), pl.col("total_points")
    yh, ya, yt = (m > 0).cast(pl.Float64), (m < 0).cast(pl.Float64), (m == 0).cast(pl.Float64)
    ev = fz.with_columns(
        ae_margin=(pl.col("pred_margin") - m).abs(),
        ae_total=(pl.col("pred_total") - t).abs(),
        ae_margin_market=(pl.col("mkt_margin") - m).abs(),
        ae_total_market=(pl.col("mkt_total") - t).abs(),
        ae_margin_football=(pl.col("fb_margin") - m).abs(),
        winner_correct=pl.when(m != 0).then((pl.col("pred_margin") > 0) == (m > 0)),
    )
    for pre in ("", "fb_"):
        ph, pa, pt = pl.col(f"{pre}p_home"), pl.col(f"{pre}p_away"), pl.col(f"{pre}p_tie")
        ev = ev.with_columns(
            pl.when(m > 0).then(ph).when(m < 0).then(pa).otherwise(pt).alias(f"{pre}p_obs"),
            ((ph - yh) ** 2 + (pa - ya) ** 2 + (pt - yt) ** 2).alias(f"{pre}brier"),     # 3-class Brier (0 = perfect)
            *[((v >= pl.col(f"{pre}{k}{lv}_lo")) & (v <= pl.col(f"{pre}{k}{lv}_hi"))).alias(f"{pre}in_{k}{lv}")
              for k, v in (("m", m), ("t", t)) for lv in (80, 95)],
        ).with_columns((-pl.col(f"{pre}p_obs").clip(1e-12, 1).log()).alias(f"{pre}log_loss"))
    return ev


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
    ev = evaluate(fz)
    ev.write_parquet(out_dir / "evaluations.parquet")
    pv = ev.filter(pl.col("verification") == "publicly_verifiable_pregame")
    summary = {"n_scored": ev.height, "by_horizon": _summary(ev) if ev.height else [],
               "n_publicly_verifiable": pv.height, "by_horizon_publicly_verifiable": _summary(pv) if pv.height else [],
               "verification_counts": ev.group_by("verification").len().sort("verification").to_dicts() if ev.height else []}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(f"[score] scored {ev.height} frozen forecasts ({pv.height} publicly verifiable)")
    return summary
