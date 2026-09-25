"""Weather: strict as-of forecast snapshot COLLECTION (prospective) and a labelled RETROSPECTIVE history.

Collection (prospective, strictly as-of): for every upcoming game, the Open-Meteo forecast API is queried for the
kickoff hour and the raw response is archived append-only (data/raw/weather/<season>/<game_id>/...json) with the
time we observed it. At most one snapshot per game every COLLECT_EVERY hours, plus one in the final 3 hours.
These snapshots are the only data that can validate weather features at genuine forecast horizons later.

Retrospective history (NOT strictly as-of): the Open-Meteo Historical Forecast API stitches short-lead forecasts;
values exist from 2019. It approximates what a same-day forecast said, not what was knowable 72 h ahead, and is
used only for the labelled retrospective feature-group evaluation.

Exposure: roof "dome"/"closed" => 0; "outdoors"/"open" => 1; unknown status at a retractable venue => 0.5.
Weather is NOT a production model input unless it passes the feature-group evaluation (evaluation/feature_groups.py).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import requests

from nflcast.config import MANUAL_DIR, RAW_DIR, utc_now, utc_stamp

VENUES_CSV = MANUAL_DIR / "venues.csv"
GEO_CACHE = MANUAL_DIR / "venue_coordinates.json"
WEATHER_DIR = RAW_DIR / "weather"
HOURLY = "temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation"
COLLECT_EVERY = timedelta(hours=3)
UA = {"User-Agent": "nflcast/0.1 (+https://github.com/INSUL4RITY/nfl-forecast)"}


def exposure(roof: str | None, retractable: bool) -> float:
    r = (roof or "").lower()
    if r in ("dome", "closed"):
        return 0.0
    if r in ("outdoors", "open"):
        return 1.0
    return 0.5 if retractable else 1.0


def venues() -> pl.DataFrame:
    """Venue table with coordinates (geocoded once via Open-Meteo, cached with the matched place name)."""
    v = pl.read_csv(VENUES_CSV, comment_prefix="#")
    cache = json.loads(GEO_CACHE.read_text(encoding="utf-8")) if GEO_CACHE.exists() else {}
    changed = False
    for r in v.iter_rows(named=True):
        if r["stadium_id"] in cache:
            continue
        res = requests.get("https://geocoding-api.open-meteo.com/v1/search", timeout=30, headers=UA,
                           params={"name": r["city"], "count": 10, "countryCode": r["country_code"]}).json().get("results", [])
        match = [x for x in res if (x.get("admin1") or "").lower() == r["admin1"].lower()] or res[:1]
        if match:
            m = match[0]
            cache[r["stadium_id"]] = {"latitude": m["latitude"], "longitude": m["longitude"], "matched": f"{m['name']}, {m.get('admin1')}, {m.get('country_code')}",
                                      "source": "open-meteo geocoding", "geocoded_at_utc": utc_now().isoformat()}
            changed = True
    if changed:
        GEO_CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
    coords = pl.DataFrame([{"stadium_id": k, "lat": c["latitude"], "lon": c["longitude"], "geo_match": c["matched"]} for k, c in cache.items()])
    return v.join(coords, on="stadium_id", how="left")


def _kickoff_row(hourly: dict, kickoff: datetime) -> dict | None:
    key = kickoff.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:00")
    times = hourly.get("time", [])
    if key not in times:
        return None
    i = times.index(key)
    vals = {k: hourly[k][i] for k in HOURLY.split(",")}
    return None if vals["wind_speed_10m"] is None else vals


# ------------------------------------------------------------------ prospective collection
def collect_snapshots(games: pl.DataFrame, now: datetime | None = None) -> int:
    """Archive a forecast snapshot for each upcoming game if due. games: game_id, season, kickoff_utc, stadium_id, roof."""
    now = now or utc_now()
    v = {r["stadium_id"]: r for r in venues().iter_rows(named=True)}
    n = 0
    for g in games.iter_rows(named=True):
        ko = g["kickoff_utc"]
        if ko <= now or ko - now > timedelta(days=15) or g["stadium_id"] not in v or v[g["stadium_id"]]["lat"] is None:
            continue
        d = WEATHER_DIR / str(g["season"]) / g["game_id"]
        d.mkdir(parents=True, exist_ok=True)
        snaps = sorted(d.glob("*.json"))
        last = datetime.fromisoformat(json.loads(snaps[-1].read_text(encoding="utf-8"))["observed_at_utc"]) if snaps else None
        final_window = ko - now <= timedelta(hours=3)
        if last and now - last < COLLECT_EVERY and not (final_window and ko - last > timedelta(hours=3)):
            continue
        ven = v[g["stadium_id"]]
        params = {"latitude": ven["lat"], "longitude": ven["lon"], "hourly": HOURLY, "timezone": "UTC",
                  "start_date": ko.strftime("%Y-%m-%d"), "end_date": ko.strftime("%Y-%m-%d")}
        try:
            r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30, headers=UA)
            body = r.json()
        except Exception as e:  # noqa: BLE001
            body, r = {"error": str(e)}, None
        rec = {"game_id": g["game_id"], "kickoff_utc": ko.isoformat(), "observed_at_utc": now.isoformat(),
               "lead_hours": round((ko - now).total_seconds() / 3600, 2), "request": {"url": "https://api.open-meteo.com/v1/forecast", **params},
               "http_status": r.status_code if r is not None else None, "roof": g["roof"],
               "exposure": exposure(g["roof"], bool(ven["retractable"])), "kickoff_hour": _kickoff_row(body.get("hourly", {}), ko),
               "response": body}
        (d / f"observed_{utc_stamp(now)}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        n += 1
    return n


def latest_snapshot(season: int, game_id: str, now: datetime) -> dict | None:
    d = WEATHER_DIR / str(season) / game_id
    best = None
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        s = json.loads(p.read_text(encoding="utf-8"))
        if datetime.fromisoformat(s["observed_at_utc"]) <= now:
            best = s
    return best


def snapshot_counts() -> dict:
    out = {}
    for season_dir in sorted(WEATHER_DIR.glob("*")) if WEATHER_DIR.exists() else []:
        out[season_dir.name] = {"games": len(list(season_dir.glob("*"))), "snapshots": len(list(season_dir.rglob("*.json")))}
    return out


# ------------------------------------------------------------------ retrospective history (labelled)
def historical_kickoff_weather(games: pl.DataFrame, cache: Path) -> pl.DataFrame:
    """Kickoff-hour weather from the Historical Forecast API (stitched, RETROSPECTIVE) for games from 2019.

    One request per (venue, season); results cached at `cache` (parquet)."""
    if cache.exists():
        return pl.read_parquet(cache)
    v = {r["stadium_id"]: r for r in venues().iter_rows(named=True)}
    rows = []
    g = games.filter((pl.col("season") >= 2019) & (pl.col("status") == "final"))
    for (sid, season), grp in g.group_by(["stadium_id", "season"]):
        ven = v.get(sid)
        if not ven or ven["lat"] is None:
            continue
        start = grp["kickoff_utc"].min().strftime("%Y-%m-%d")
        end = (grp["kickoff_utc"].max() + timedelta(days=1)).strftime("%Y-%m-%d")
        body = requests.get("https://historical-forecast-api.open-meteo.com/v1/forecast", timeout=120, headers=UA, params={
            "latitude": ven["lat"], "longitude": ven["lon"], "start_date": start, "end_date": end, "hourly": HOURLY,
            "timezone": "UTC"}).json()
        for r in grp.iter_rows(named=True):
            k = _kickoff_row(body.get("hourly", {}), r["kickoff_utc"])
            if k is None:
                continue
            rows.append({"game_id": r["game_id"], "temp_c": k["temperature_2m"], "wind_kmh": k["wind_speed_10m"],
                         "gust_kmh": k["wind_gusts_10m"], "precip_mm": k["precipitation"],
                         "exposure": exposure(r["roof"], bool(ven["retractable"]))})
    df = pl.DataFrame(rows)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(cache)
    return df


def weather_features(df: pl.DataFrame) -> pl.DataFrame:
    """Exposure-weighted weather features (0 under a closed roof)."""
    return df.with_columns(
        wx_wind=pl.col("wind_kmh") * pl.col("exposure"),
        wx_gust=pl.col("gust_kmh") * pl.col("exposure"),
        wx_cold=(10.0 - pl.col("temp_c")).clip(0, None) * pl.col("exposure"),
        wx_precip=pl.col("precip_mm") * pl.col("exposure"),
        wx_exposed=pl.col("exposure"))


WX_FEATURES = ["wx_wind", "wx_gust", "wx_cold", "wx_precip", "wx_exposed"]
