"""Prospective data collection run every operate cycle: weather forecast snapshots and injury-report versions."""

from __future__ import annotations

import polars as pl

from nflcast.config import settings, utc_now
from nflcast.data import sources as S
from nflcast.data.games import build_games
from nflcast.features import injury_versions, weather


def collect() -> dict:
    now = utc_now()
    season = settings()["seasons"]["current"]
    games = build_games(S.fetch("schedules")).filter((pl.col("status") == "scheduled") & (pl.col("kickoff_utc") > now))
    n_wx = weather.collect_snapshots(games, now)
    inj = injury_versions.collect(season)
    return {"weather_snapshots_written": n_wx, "weather_archive": weather.snapshot_counts(), "injury_versions": inj}
