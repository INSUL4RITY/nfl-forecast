"""Build the `games` table (fixtures, venue, kickoff in UTC, outcomes) and the `market` table.

Sign convention (used everywhere in this project):
    H = home points, A = away points, M = H - A (home margin), T = H + A.
    home_spread s: the home team's quoted spread, NEGATIVE when home is favoured.
nflverse `spread_line` is the expected home margin (positive = home favoured), verified in the
audit by its positive correlation with the realised home margin, so s = -spread_line and the
raw market benchmark is M0 = -s = spread_line, T0 = total_line.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from nflcast.config import MANUAL_DIR, RAW_DIR, settings
from nflcast.data import sources as S
from nflcast.data.policy import assert_no_banned

# Relocated franchises -> stable franchise id (the current nflverse code).
FRANCHISE_ALIAS = {"OAK": "LV", "SD": "LAC", "STL": "LA"}


def franchise(expr: pl.Expr) -> pl.Expr:
    return expr.replace(FRANCHISE_ALIAS)


def build_games(schedules: pl.DataFrame | None = None) -> pl.DataFrame:
    cfg = settings()
    sch = schedules if schedules is not None else S.fetch("schedules")
    tz = cfg["schedule_timezone"]
    kickoff_local = pl.concat_str([pl.col("gameday"), pl.col("gametime").fill_null("13:00")], separator=" ").str.strptime(
        pl.Datetime("us"), "%Y-%m-%d %H:%M", strict=False)
    g = sch.with_columns(
        kickoff_utc=kickoff_local.dt.replace_time_zone(tz, ambiguous="earliest").dt.convert_time_zone("UTC"),
        kickoff_time_known=pl.col("gametime").is_not_null(),
        home_id=franchise(pl.col("home_team")),
        away_id=franchise(pl.col("away_team")),
        neutral_site=(pl.col("location") == "Neutral"),
        is_playoff=(pl.col("game_type") != "REG"),
        margin=(pl.col("home_score") - pl.col("away_score")).cast(pl.Float64),
        total_points=(pl.col("home_score") + pl.col("away_score")).cast(pl.Float64),
    ).with_columns(
        status=pl.when(pl.col("home_score").is_not_null()).then(pl.lit("final")).otherwise(pl.lit("scheduled")),
    )
    cols = ["game_id", "season", "week", "game_type", "is_playoff", "gameday", "weekday", "gametime", "kickoff_utc",
            "kickoff_time_known", "home_team", "away_team", "home_id", "away_id", "neutral_site", "stadium_id", "stadium",
            "roof", "surface", "div_game", "home_rest", "away_rest", "home_qb_id", "away_qb_id", "home_qb_name",
            "away_qb_name", "home_coach", "away_coach", "status",
            # outcomes partition (never used as features)
            "home_score", "away_score", "margin", "total_points", "overtime"]
    return g.select(cols).sort(["kickoff_utc", "game_id"])


OUTCOME_COLUMNS = {"home_score", "away_score", "margin", "total_points", "overtime", "result", "total"}


def schedule_market_snapshots() -> pl.DataFrame:
    """All archived schedule snapshots -> market rows (game_id, snapshot time, home_spread, total).

    The provider does not timestamp lines. For snapshots *we* archived, `observed_at` is our retrieval
    time: the line was public no later than that. For historical seasons the line's timing is unknown
    and is labelled `approx_closing`.
    """
    rows = []
    d = RAW_DIR / "schedules" / "all"
    for meta_path in sorted(d.glob("*.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        snap = pl.read_parquet(meta_path.with_suffix(".parquet")).select(
            "game_id", "season", "spread_line", "total_line", "home_score")
        rows.append(snap.with_columns(
            observed_at=pl.lit(meta["observed_at_utc"]).str.to_datetime(time_zone="UTC"),
            http_last_modified=pl.lit(meta.get("http_last_modified")),
        ))
    if not rows:
        return pl.DataFrame()
    return pl.concat(rows, how="diagonal_relaxed")


def load_manual_market_csv() -> pl.DataFrame:
    """Documented CSV import route for timestamped lines from any provider.

    Expected columns: game_id, source, snapshot_at (ISO-8601 UTC), home_spread (negative = home favoured), total.
    Any other columns are ignored; price-type columns are rejected outright.
    """
    folder = MANUAL_DIR / "market_snapshots"
    files = sorted(folder.glob("*.csv")) if folder.exists() else []
    if not files:
        return pl.DataFrame(schema={"game_id": pl.Utf8, "source": pl.Utf8, "snapshot_at": pl.Datetime("us", "UTC"),
                                    "home_spread": pl.Float64, "total": pl.Float64})
    frames = []
    for f in files:
        df = pl.read_csv(f)
        assert_no_banned(df.columns, context=f"in {f.name}")
        frames.append(df.select(
            pl.col("game_id").cast(pl.Utf8), pl.col("source").cast(pl.Utf8),
            pl.col("snapshot_at").str.to_datetime(time_zone="UTC"),
            pl.col("home_spread").cast(pl.Float64), pl.col("total").cast(pl.Float64)))
    return pl.concat(frames)


def market_asof(games: pl.DataFrame, cutoffs: pl.DataFrame, allow_approx_closing: bool) -> pl.DataFrame:
    """Market lines usable at each (game_id, cutoff_utc).

    Priority: (1) manual CSV snapshots at or before cutoff, (2) our archived schedule snapshots observed
    at or before cutoff, (3) if `allow_approx_closing`, the single historical schedule line labelled
    `approx_closing` (only for completed historical games at the final-pregame horizon).
    Returns one row per input (game_id, cutoff_utc) with nulls where no line is available.
    """
    base = cutoffs.select("game_id", "cutoff_utc", "horizon")
    cands = []
    man = load_manual_market_csv()
    if man.height:
        cands.append(man.select("game_id", pl.col("snapshot_at"), "home_spread", "total",
                                pl.col("source").alias("market_source"), pl.lit("timestamped").alias("market_timing")))
    snaps = schedule_market_snapshots()
    if snaps.height:
        live = snaps.filter(pl.col("spread_line").is_not_null() & pl.col("home_score").is_null())
        cands.append(live.select("game_id", pl.col("observed_at").alias("snapshot_at"),
                                 (-pl.col("spread_line")).alias("home_spread"), pl.col("total_line").alias("total"),
                                 pl.lit("nflverse_schedules_archived").alias("market_source"),
                                 pl.lit("observed_by_us").alias("market_timing")))
    out = base
    if cands:
        allc = pl.concat(cands, how="diagonal_relaxed").sort("snapshot_at")
        j = base.join(allc, on="game_id", how="inner").filter(pl.col("snapshot_at") <= pl.col("cutoff_utc"))
        latest = j.sort("snapshot_at").group_by(["game_id", "cutoff_utc", "horizon"]).last()
        out = base.join(latest, on=["game_id", "cutoff_utc", "horizon"], how="left")
    else:
        out = base.with_columns(snapshot_at=pl.lit(None, pl.Datetime("us", "UTC")), home_spread=pl.lit(None, pl.Float64),
                                total=pl.lit(None, pl.Float64), market_source=pl.lit(None, pl.Utf8), market_timing=pl.lit(None, pl.Utf8))
    if allow_approx_closing:
        hist = S.fetch("schedules").filter(pl.col("home_score").is_not_null()).select(
            "game_id", (-pl.col("spread_line")).alias("_hs"), pl.col("total_line").alias("_tot"))
        out = out.join(hist, on="game_id", how="left").with_columns(
            _use=pl.col("home_spread").is_null() & pl.col("_hs").is_not_null() & (pl.col("horizon") == "final"))
        out = out.with_columns(
            home_spread=pl.when(pl.col("_use")).then(pl.col("_hs")).otherwise(pl.col("home_spread")),
            total=pl.when(pl.col("_use")).then(pl.col("_tot")).otherwise(pl.col("total")),
            market_source=pl.when(pl.col("_use")).then(pl.lit("nflverse_schedules_historical")).otherwise(pl.col("market_source")),
            market_timing=pl.when(pl.col("_use")).then(pl.lit("approx_closing")).otherwise(pl.col("market_timing")),
        ).drop("_hs", "_tot", "_use")
    return out.with_columns(market_available=pl.col("home_spread").is_not_null() & pl.col("total").is_not_null())
