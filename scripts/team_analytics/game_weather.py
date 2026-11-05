"""Weather line for the coming week's games: forecast at each venue plus what similar games did in the past.

Forecast: National Weather Service hourly forecast for US venues, Open-Meteo for other venues or when NWS cannot be read
(neither needs a key), for the kickoff hour and the next three hours. Rain or snow counts as likely at a 50%+ chance of precipitation in any of those hours; wind is the mean over them. Indoor games have no forecast; a
blank nflverse roof means open or closed is not known yet, so the forecast is shown without any history.

History: raw averages from all outdoor and open-roof 2021-25 regular-season games with a usable weather text, grouped
by the conditions in the play-by-play weather text. Not adjusted for teams. Display only: no rating, edge or expected
figure changes.

Add the line to an existing report folder (it then updates with refresh_status.py):
    .venv\\Scripts\\python.exe scripts\\team_analytics\\game_weather.py --dir reports\\team_analytics\\2026_week10
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context as ctx  # noqa: E402

URL = "https://api.open-meteo.com/v1/forecast"
NWS = "https://api.weather.gov/points/{lat:.4f},{lon:.4f}"
NWS_SNOW = re.compile(r"snow|sleet|flurr|wintry", re.I)
HOURLY = "temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m"
UA = {"User-Agent": "nflcast-team-analytics"}
ET = ZoneInfo("America/New_York")
WET_POP = 50
SOME_POP = 20
WIND_MIN = 15
WINDOW_H = 4
EARLY_DAYS = 3
SNOW_CODES = {71, 73, 75, 77, 85, 86}
RAIN = re.compile(r"rain|shower|drizzle|storm", re.I)
SNOW = re.compile(r"snow|sleet|flurr|flakes", re.I)
BASE = "calm_dry"
BUCKETS = {
    "calm_dry": "dry conditions and wind under 15 mph",
    "wind": "dry conditions and wind of 15+ mph",
    "rain": "rain and wind under 15 mph",
    "rain_wind": "rain and wind of 15+ mph",
    "snow": "snow",
}


def bucket(wet: bool, snow: bool, wind) -> str | None:
    """Weather group; None when the wind is needed and missing."""
    if snow:
        return "snow"
    if wind is None:
        return None
    if wet:
        return "rain_wind" if wind >= WIND_MIN else "rain"
    return "wind" if wind >= WIND_MIN else "calm_dry"


def text_bucket(text, roof) -> str | None:
    """Group for a past game from its play-by-play weather text, e.g. 'Rain Temp: 78 F, Humidity: 81%, Wind: E 9 mph'."""
    if str(roof) not in ("outdoors", "open") or not isinstance(text, str) or not text.strip():
        return None
    cond = text.split("Temp")[0]
    w = re.search(r"(\d+)\s*mph", text)
    wet = bool(RAIN.search(cond)) and not SNOW.search(cond)
    return bucket(wet, bool(SNOW.search(cond)), int(w.group(1)) if w else None)


def history(seasons_pbp: dict, hist: list) -> dict:
    fr = []
    for s in hist:
        p = seasons_pbp[s]
        p = p[p.sc]
        g = p.groupby("game_id").agg(w=("weather", "first"), r=("roof", "first"))
        fr.append(p.assign(group=p.game_id.map({i: text_bucket(a, b) for i, a, b in zip(g.index, g.w, g.r)})))
    a = pd.concat(fr)
    used = a[a.group.notna()]
    out = {}
    for k in BUCKETS:
        x = used[used.group == k]
        db, ru = x[x.db], x[(x["rush"] == 1) & ~x.db]
        close = x[x.wp.between(0.2, 0.8)]
        out[k] = {"games": int(x.game_id.nunique()), "pass_rate": float(close.db.mean()), "epa_db": float(db.epa.mean()),
                  "epa_rush": float(ru.epa.mean()), "ypc": float(ru.yards_gained.mean())}
    return {"years": [hist[0], hist[-1]], "groups": out, "games_used": int(used.game_id.nunique())}


def kickoff(g) -> dt.datetime:
    d = dt.datetime.strptime(f"{g.gameday} {g.gametime}", "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    return d.astimezone(dt.timezone.utc)


def game_window(body: dict, ko: dt.datetime) -> dict | None:
    """Summarise the kickoff hour and the next three hours of an Open-Meteo response (hourly times in UTC)."""
    h = body.get("hourly") or {}
    start = ko.replace(minute=0, second=0, microsecond=0)
    want = [(start + dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(WINDOW_H)]
    times = h.get("time") or []
    idx = [times.index(t) for t in want if t in times]
    if len(idx) < WINDOW_H:
        return None
    col = lambda k: [h[k][i] for i in idx]   # noqa: E731
    if any(v is None for k in ("temperature_2m", "wind_speed_10m") for v in col(k)):
        return None
    pop = [v for v in col("precipitation_probability") if v is not None]
    return {"temp": float(col("temperature_2m")[0]), "wind": sum(col("wind_speed_10m")) / WINDOW_H, "gust": max(v or 0 for v in col("wind_gusts_10m")),
            "pop": max(pop) if pop else None, "inches": sum(v or 0 for v in col("precipitation")), "snow": any(v in SNOW_CODES for v in col("weather_code"))}


def nws_window(periods: list, ko: dt.datetime) -> dict | None:
    """Same summary from NWS hourly periods. NWS hourly data has no gusts or precipitation amounts."""
    start = ko.replace(minute=0, second=0, microsecond=0)
    by_hour = {dt.datetime.fromisoformat(p["startTime"]).astimezone(dt.timezone.utc): p for p in periods}
    hours = [by_hour.get(start + dt.timedelta(hours=i)) for i in range(WINDOW_H)]
    if any(p is None for p in hours):
        return None
    wind = [re.search(r"(\d+)\s*mph$", str(p.get("windSpeed"))) for p in hours]
    if not all(wind):
        return None
    pop = [(p.get("probabilityOfPrecipitation") or {}).get("value") for p in hours]
    pop = [v for v in pop if v is not None]
    return {"temp": float(hours[0]["temperature"]), "wind": sum(int(w.group(1)) for w in wind) / WINDOW_H, "gust": None, "pop": max(pop) if pop else None,
            "inches": None, "snow": any(NWS_SNOW.search(str(p.get("shortForecast"))) for p in hours)}


def fetch_nws(lat, lon, ko: dt.datetime, get=requests.get) -> dict | None:
    try:
        r = get(NWS.format(lat=lat, lon=lon), headers=UA, timeout=30)
        r.raise_for_status()
        h = get(r.json()["properties"]["forecastHourly"], headers=UA, timeout=30)
        h.raise_for_status()
        return nws_window(h.json()["properties"]["periods"], ko)
    except Exception:  # noqa: BLE001
        return None


def fetch_open_meteo(lat, lon, ko: dt.datetime, get=requests.get) -> dict | None:
    """One game's forecast, or None if it cannot be read. A failure must never stop a report."""
    params = {"latitude": lat, "longitude": lon, "hourly": HOURLY, "timezone": "UTC", "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
              "precipitation_unit": "inch", "start_date": ko.strftime("%Y-%m-%d"), "end_date": (ko + dt.timedelta(days=1)).strftime("%Y-%m-%d")}
    try:
        r = get(URL, params=params, headers=UA, timeout=30)
        r.raise_for_status()
        return game_window(r.json(), ko)
    except Exception:  # noqa: BLE001
        return None


def game_record(g, now: dt.datetime, get=requests.get) -> dict:
    ko = kickoff(g)
    rec = {"kickoff_utc": ko.isoformat(timespec="minutes")}
    if ko <= now:
        return rec | {"kind": "started"}
    roof = "" if pd.isna(g.roof) else str(g.roof)
    if roof in ("dome", "closed"):
        return rec | {"kind": "indoors"}
    lat, lon, _, _ = ctx.venue_geo(g)
    if pd.isna(lat):
        return rec | {"kind": "none"}
    fc = fetch_nws(lat, lon, ko, get) if str(g.location) != "Neutral" else None
    source = "National Weather Service"
    if fc is None:
        fc, source = fetch_open_meteo(lat, lon, ko, get), "Open-Meteo"
    if fc is None:
        return rec | {"kind": "none"}
    return rec | {"kind": "forecast" if roof in ("outdoors", "open") else "roof_unknown", "source": source, "read_utc": now.isoformat(timespec="minutes"),
                  "lead_days": round((ko - now).total_seconds() / 86400, 1)} | fc


def conditions(r: dict) -> tuple[str, str | None]:
    """(plain label, weather group) for a forecast."""
    pop = r["pop"]
    wet = pop is not None and pop >= WET_POP
    snow = wet and r["snow"]
    label = "Snow likely" if snow else "Rain likely" if wet else "Dry" if pop is not None and pop < SOME_POP else "Some chance of rain"
    return label, bucket(wet and not snow, snow, r["wind"])


def history_text(group: str, H: dict) -> str:
    x, b = H["groups"][group], H["groups"][BASE]
    y0, y1 = H["years"]
    return (f"In {y0}-{str(y1)[-2:]} games with {BUCKETS[group]} ({x['games']} games), teams passed on {x['pass_rate']:.1%} of plays in close games "
            f"({b['pass_rate']:.1%} with {BUCKETS[BASE]}), EPA/dropback {x['epa_db']:+.3f} ({b['epa_db']:+.3f}), EPA/rush {x['epa_rush']:+.3f} ({b['epa_rush']:+.3f}). "
            "Raw averages, not adjusted for teams.")


def line(r: dict, H: dict) -> str | None:
    """The sentence shown on a matchup; None once the game has started."""
    k = r.get("kind")
    if k == "started":
        return None
    if k == "indoors":
        return "Indoors, so no weather effect."
    if k != "forecast" and k != "roof_unknown":
        return "Forecast not loaded."
    label, group = conditions(r)
    pop = "chance of precipitation not given" if r["pop"] is None else f"{r['pop']:.0f}% chance of precipitation"
    amount = f", {r['inches']:.2f} in forecast" if r["inches"] is not None and label in ("Rain likely", "Snow likely") else ""
    gust = "" if r["gust"] is None else f" (gusts {r['gust']:.0f})"
    when = dt.datetime.fromisoformat(r["read_utc"]).strftime("%d %b %H:%M UTC")
    early = f"; early forecast, {r['lead_days']:.0f} days before kickoff" if r["lead_days"] >= EARLY_DAYS else ""
    head = f"{label}: {r['temp']:.0f}°F at kickoff, wind {r['wind']:.0f} mph{gust}, {pop}{amount} ({r['source']}, read {when}{early})."
    if k == "roof_unknown":
        return f"Roof not listed, so open or closed is not known yet. If open: {head}"
    return head if group in (None, BASE) else f"{head} {history_text(group, H)}"


def build(seasons_pbp: dict, hist: list, nxt: pd.DataFrame, get=requests.get) -> dict:
    return update({"history": history(seasons_pbp, hist)}, nxt, get)


def update(prev: dict, nxt: pd.DataFrame, get=requests.get) -> dict:
    """New forecasts for the schedule. A game whose forecast cannot be re-read keeps the last one, with its read time."""
    now = dt.datetime.now(dt.timezone.utc)
    H, old, games = prev["history"], prev.get("games", {}), {}
    for g in nxt.itertuples():
        rec = game_record(g, now, get)
        if rec["kind"] == "none" and old.get(g.game_id, {}).get("kind") in ("forecast", "roof_unknown"):
            rec = old[g.game_id]
        games[g.game_id] = rec | {"text": line(rec, H)}
    return {"history": H, "games": games, "wet_pop": WET_POP, "wind_min": WIND_MIN}


def qc_line(W: dict) -> str:
    kinds = [g["kind"] for g in W["games"].values()]
    n = lambda *k: sum(x in k for x in kinds)   # noqa: E731
    return (f"Weather: {n('forecast')} forecasts, {n('roof_unknown')} with the roof not listed, {n('indoors')} indoors, {n('started')} already started, "
            f"{n('none')} not loaded. History from {W['history']['games_used']} outdoor games with a usable weather text.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    import compute as cp  # noqa: PLC0415
    d = Path(a.dir)
    meta = json.loads((d / "bundle_meta.json").read_text())
    hist = list(range(2021, int(meta["season"])))
    seasons = {s: cp.add_unit_flags(cp.load_pbp(s)) for s in hist}
    W = build(seasons, hist, pd.read_csv(d / "next_week_schedule.csv"))
    (d / "weather.json").write_text(json.dumps(W, indent=1, default=str), encoding="utf-8")
    meta["qc"] = [q for q in meta["qc"] if not q.startswith("Weather")] + [qc_line(W)]
    (d / "bundle_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print(qc_line(W))
    here = Path(__file__).resolve().parent
    for script in ("build_html.py", "export_games.py"):
        subprocess.run([sys.executable, str(here / script), "--dir", str(d)], check=True)


if __name__ == "__main__":
    main()
