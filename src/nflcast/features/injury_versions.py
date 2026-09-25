"""Non-QB (and QB) injury-report VERSION collection for prospective as-of evaluation.

nflverse keeps only the latest weekly record per player; earlier intra-week versions are lost. Every archived
injury snapshot (data/raw/injuries/<season>/, append-only, written whenever the content changes) is expanded
here into one row per (player-week, status, practice) version with the time we first observed it and the last
time it was confirmed unchanged. Over a season this builds the as-of history needed to evaluate early-horizon
injury features and to calibrate mid-week practice readings; it cannot be reconstructed for past seasons.
"""

from __future__ import annotations

import json
from datetime import datetime

import polars as pl

from nflcast.config import PROCESSED_DIR, RAW_DIR
from nflcast.data.games import franchise

OUT = PROCESSED_DIR / "injury_versions.parquet"


def build(season: int) -> pl.DataFrame:
    d = RAW_DIR / "injuries" / str(season)
    frames = []
    checks = {}
    if (d / "checks.jsonl").exists():
        for line in (d / "checks.jsonl").read_text(encoding="utf-8").splitlines():
            c = json.loads(line)
            checks[c["content_sha256"]] = max(checks.get(c["content_sha256"], ""), c["checked_at_utc"])
    for meta_p in sorted(d.glob("*.json")) if d.exists() else []:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        df = pl.read_parquet(meta_p.with_suffix(".parquet"))
        frames.append(df.select(
            pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), franchise(pl.col("team")).alias("team"),
            "gsis_id", "full_name", "position", "report_status", "practice_status",
            pl.col("report_primary_injury").alias("injury") if "report_primary_injury" in df.columns else pl.lit(None).alias("injury"),
        ).with_columns(observed_at=pl.lit(meta["observed_at_utc"]).str.to_datetime(time_zone="UTC"),
                       confirmed_until=pl.lit(max(meta["observed_at_utc"], checks.get(meta["content_sha256"], ""))).str.to_datetime(time_zone="UTC"),
                       provider_last_modified=pl.lit(meta.get("http_last_modified")),
                       snapshot_sha256=pl.lit(meta["content_sha256"])))
    if not frames:
        return pl.DataFrame()
    allv = pl.concat(frames, how="diagonal_relaxed")
    key = ["season", "week", "team", "gsis_id"]
    vals = ["report_status", "practice_status"]
    versions = (allv.sort("observed_at")
                .group_by(key + vals, maintain_order=True)
                .agg(pl.col("full_name").first(), pl.col("position").first(), pl.col("injury").first(),
                     first_observed_at=pl.col("observed_at").min(), last_confirmed_at=pl.col("confirmed_until").max(),
                     provider_last_modified=pl.col("provider_last_modified").first(), n_snapshots=pl.len()))
    return versions.sort(key + ["first_observed_at"])


def collect(season: int) -> dict:
    v = build(season)
    if v.height:
        v.write_parquet(OUT)
    non_qb = v.filter(pl.col("position") != "QB") if v.height else v
    return {"season": season, "player_week_versions": v.height,
            "player_weeks": v.select(["season", "week", "team", "gsis_id"]).unique().height if v.height else 0,
            "non_qb_versions": non_qb.height, "snapshots": len(list((RAW_DIR / "injuries" / str(season)).glob("*.parquet"))),
            "first_snapshot": str(v["first_observed_at"].min()) if v.height else None}
