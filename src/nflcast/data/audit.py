"""Milestone 1: data availability audit.

Measures (does not assume) what each free source actually provides: which season files exist,
schemas, key-field completeness, and whether the source carries the timestamps needed to know
what was available *before* a forecast cutoff. Results are written to reports/audit/.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import date, timedelta
from importlib.metadata import version

import polars as pl
import requests

from nflcast.config import REPORTS_DIR, settings, utc_now, utc_stamp
from nflcast.data import sources as S

AUDIT_DIR = REPORTS_DIR / "audit"


def _null_frac(df: pl.DataFrame, cols: list[str]) -> dict:
    return {c: round(df[c].null_count() / max(df.height, 1), 4) for c in cols if c in df.columns}


def _ts_like(df: pl.DataFrame) -> list[str]:
    keys = ("date", "time", "dt", "modified", "pulled", "updated", "_at")
    out = []
    for c, t in df.schema.items():
        if t in (pl.Datetime, pl.Date) or isinstance(t, pl.Datetime) or any(k in c.lower() for k in keys):
            out.append(c)
    return out


def season_file_coverage(current: int) -> dict:
    cov = {}
    for name, src in S.SOURCES.items():
        if not src.per_season:
            cov[name] = {"single_file": S.head(src)}
            continue
        rows = {}
        for season in range(src.min_season, current + 1):
            h = S.head(src, season)
            rows[season] = {k: h.get(k) for k in ("exists", "bytes", "last_modified")}
        existing = [s for s, r in rows.items() if r["exists"]]
        cov[name] = {
            "documented_min_season": src.min_season,
            "measured_first": min(existing) if existing else None,
            "measured_last": max(existing) if existing else None,
            "missing_seasons": [s for s, r in rows.items() if not r["exists"]],
            "per_season": rows,
        }
    return cov


def audit_schedules() -> dict:
    df = S.fetch("schedules", refresh=True)
    meta = json.loads(sorted((S.RAW_DIR / "schedules" / "all").glob("*.json"))[-1].read_text(encoding="utf-8"))
    by = (df.group_by("season").agg(
        games=pl.len(),
        completed=pl.col("result").is_not_null().sum(),
        spread_missing=pl.col("spread_line").is_null().sum(),
        total_missing=pl.col("total_line").is_null().sum(),
        neutral=(pl.col("location") == "Neutral").sum(),
        playoff=(pl.col("game_type") != "REG").sum(),
        ties=(pl.col("result") == 0).sum(),
        overtime=pl.col("overtime").sum(),
        qb_id_missing=pl.col("home_qb_id").is_null().sum(),
        temp_missing=pl.col("temp").is_null().sum(),
        wind_missing=pl.col("wind").is_null().sum(),
    ).sort("season"))
    done = df.filter(pl.col("result").is_not_null() & pl.col("spread_line").is_not_null())
    sign_corr = done.select(pl.corr("spread_line", "result")).item()
    return {
        "rows": df.height, "columns": df.columns,
        "dropped_price_columns_at_ingest": meta["dropped_price_columns"],
        "http_last_modified": meta["http_last_modified"],
        "per_season": by.to_dicts(),
        "spread_sign_check": {
            "corr_spread_line_vs_home_margin": round(sign_corr, 4),
            "interpretation": "positive => nflverse spread_line is the expected HOME margin (home favoured when > 0); "
                              "project home_spread s = -spread_line",
        },
        "line_timestamp_available": False,
        "note": "Schedule lines are a single value per game with no snapshot timestamp; treated as an approximately "
                "closing/final-pregame line, not an opening or 72h line.",
        "weather_fields_note": "temp/wind in schedules are game-time observations (post-hoc), not pregame forecasts.",
    }


def audit_pbp(seasons: list[int]) -> dict:
    out = {}
    for s in seasons:
        df = S.fetch("pbp", s, refresh=False)
        out[s] = {
            "rows": df.height, "n_columns": len(df.columns),
            "games": df["game_id"].n_unique(),
            "null_frac": _null_frac(df.filter(pl.col("pass") == 1), ["epa", "cpoe", "air_yards", "wp", "success"]),
            "has_vegas_columns_after_strip": [c for c in df.columns if "vegas" in c],
        }
    return out


def audit_injuries(seasons: list[int]) -> dict:
    out = {}
    for s in seasons:
        try:
            df = S.fetch("injuries", s, refresh=False)
        except Exception as e:  # noqa: BLE001
            out[s] = {"error": str(e)}
            continue
        key = [c for c in ("season", "week", "team", "gsis_id") if c in df.columns]
        per_key = df.group_by(key).len()["len"]
        out[s] = {
            "rows": df.height, "columns": df.columns, "timestamp_like_columns": _ts_like(df),
            "weeks": sorted(df["week"].unique().drop_nulls().to_list()) if "week" in df.columns else None,
            "max_records_per_player_week": int(per_key.max()) if per_key.len() else 0,
            "report_status_counts": df["report_status"].value_counts().sort("count", descending=True).to_dicts()
            if "report_status" in df.columns else None,
            "practice_status_counts": df["practice_status"].value_counts().sort("count", descending=True).head(8).to_dicts()
            if "practice_status" in df.columns else None,
            "gsis_id_null_frac": _null_frac(df, ["gsis_id"]).get("gsis_id"),
        }
    return out


def audit_depth_charts(seasons: list[int]) -> dict:
    out = {}
    for s in seasons:
        try:
            df = S.fetch("depth_charts", s, refresh=False)
        except Exception as e:  # noqa: BLE001
            out[s] = {"error": str(e)}
            continue
        info = {"rows": df.height, "columns": df.columns, "timestamp_like_columns": _ts_like(df)}
        if "dt" in df.columns:
            dts = df["dt"].cast(pl.Utf8).str.slice(0, 10).unique().sort()
            info.update({"distinct_snapshot_days": dts.len(), "first_dt": dts.min(), "last_dt": dts.max()})
        if "week" in df.columns:
            info["weeks"] = sorted(df["week"].unique().drop_nulls().to_list())
        out[s] = info
    return out


def audit_ftn(sched: pl.DataFrame, seasons: list[int]) -> dict:
    out = {}
    for s in seasons:
        try:
            df = S.fetch("ftn_charting", s, refresh=False)
        except Exception as e:  # noqa: BLE001
            out[s] = {"error": str(e)}
            continue
        info = {"rows": df.height, "games": df["nflverse_game_id"].n_unique(), "columns": df.columns}
        if "date_pulled" in df.columns:
            g = (df.group_by("nflverse_game_id").agg(pl.col("date_pulled").min().alias("pulled"))
                 .join(sched.select(pl.col("game_id").alias("nflverse_game_id"), "gameday"), on="nflverse_game_id", how="left")
                 .with_columns(lag_days=(pl.col("pulled").cast(pl.Utf8).str.slice(0, 10).str.to_date()
                                         - pl.col("gameday").str.to_date()).dt.total_days()))
            lag = g["lag_days"].drop_nulls()
            info["date_pulled_lag_days_after_game"] = {
                "min": lag.min(), "median": lag.median(), "p90": lag.quantile(0.9), "max": lag.max(),
                "note": "date_pulled is the latest pull; it is an upper bound on public availability, not first publication.",
            }
        out[s] = info
    return out


def audit_generic(name: str, seasons: list[int], key_cols: list[str]) -> dict:
    out = {}
    for s in seasons:
        try:
            df = S.fetch(name, s, refresh=False)
        except Exception as e:  # noqa: BLE001
            out[s] = {"error": str(e)}
            continue
        info = {"rows": df.height, "columns": df.columns, "timestamp_like_columns": _ts_like(df),
                "null_frac": _null_frac(df, key_cols)}
        if "week" in df.columns:
            info["weeks"] = sorted(df["week"].unique().drop_nulls().to_list())
        out[s] = info
    return out


def audit_single(name: str) -> dict:
    df = S.fetch(name, refresh=True)
    info = {"rows": df.height, "columns": df.columns}
    if "season" in df.columns:
        info["seasons"] = sorted(df["season"].unique().drop_nulls().to_list())
    return info


def audit_weather() -> dict:
    """Probe Open-Meteo: stitched historical-forecast series vs archived single operational runs."""
    lat, lon = 39.049, -94.484  # Arrowhead Stadium, a fixed probe location
    res = {}
    hf = requests.get("https://historical-forecast-api.open-meteo.com/v1/forecast", timeout=30, params={
        "latitude": lat, "longitude": lon, "start_date": "2018-10-14", "end_date": "2018-10-14",
        "hourly": "wind_speed_10m", "timezone": "UTC"})
    res["historical_forecast_api_2018"] = {"status": hf.status_code, "ok": hf.ok,
                                           "note": "Stitched series of short-lead forecasts; NOT the forecast known 72h before kickoff."}
    # Find the earliest available single operational run by stepping back week by week.
    # Start a few days back: today's run may not be published yet.
    earliest, probe = None, date.today() - timedelta(days=3)
    for _ in range(80):
        r = requests.get("https://single-runs-api.open-meteo.com/v1/forecast", timeout=30, params={
            "latitude": lat, "longitude": lon, "run": f"{probe.isoformat()}T00:00", "hourly": "wind_speed_10m",
            "models": "gfs_seamless", "forecast_days": 4, "timezone": "UTC"})
        if not r.ok:
            break
        earliest = probe.isoformat()
        probe -= timedelta(days=7)
    res["single_runs_api_gfs"] = {
        "earliest_available_run_found": earliest,
        "search": "weekly steps back from today until the first unavailable run",
        "note": "Only runs inside this window can support strict as-of weather features.",
    }
    return res


def run(quick: bool = False) -> dict:
    cfg = settings()
    current = cfg["seasons"]["current"]
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    report = {
        "generated_at_utc": utc_now().isoformat(),
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "packages": {p: version(p) for p in ("nflreadpy", "polars", "scikit-learn", "numpy", "duckdb")}},
    }
    print("[audit] season file coverage (HTTP HEAD)...")
    report["file_coverage"] = season_file_coverage(current)
    print("[audit] schedules...")
    report["schedules"] = audit_schedules()
    sched = S.fetch("schedules")
    sample = [2016, 2021, 2025, current] if not quick else [2025]
    print("[audit] play-by-play...")
    report["pbp"] = audit_pbp([2006, 2016, 2025, current] if not quick else [2025])
    print("[audit] injuries...")
    report["injuries"] = audit_injuries([2009, 2015, 2019, 2022, 2024, 2025, current] if not quick else [2025])
    print("[audit] depth charts...")
    report["depth_charts"] = audit_depth_charts([2016, 2023, 2024, 2025, current] if not quick else [2025])
    print("[audit] rosters / snaps / participation / pfr...")
    report["rosters_weekly"] = audit_generic("rosters_weekly", sample, ["gsis_id", "status", "depth_chart_position"])
    report["snap_counts"] = audit_generic("snap_counts", sample, ["pfr_player_id", "offense_pct"])
    part_seasons = [s for s in (2016, 2022, 2023, 2024, 2025, current)
                    if report["file_coverage"]["participation"]["per_season"].get(s, {}).get("exists")]
    report["participation"] = audit_generic("participation", part_seasons, ["was_pressure", "time_to_throw", "defense_coverage_type", "route"])
    report["pfr_advstats_week_pass"] = audit_generic("pfr_advstats_week_pass", [2018, 2025, current], ["times_pressured", "passing_bad_throws"])
    print("[audit] FTN charting...")
    report["ftn_charting"] = audit_ftn(sched, [2022, 2023, 2024, 2025, current] if not quick else [2025])
    print("[audit] single-file sources...")
    for name in ("nextgen_passing", "officials", "teams"):
        report[name] = audit_single(name)
    print("[audit] weather APIs...")
    report["weather"] = audit_weather()
    report["market_snapshots"] = {
        "free_timestamped_history": False,
        "schedule_lines": "single line per game, no timestamp (see schedules)",
        "the_odds_api": "Timestamped historical snapshots documented as a paid plan; not subscribed, no key assumed.",
        "fallback": "CSV import route (data/manual/market_snapshots/*.csv) + prospective snapshot archiving from now on.",
    }
    path = AUDIT_DIR / f"audit_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (AUDIT_DIR / "audit_latest.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"[audit] wrote {path}")
    return report
