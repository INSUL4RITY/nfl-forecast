"""The Odds API market feed (free plan): NFL full-game point spreads and totals ONLY.

Request: GET {endpoint}?regions=us&markets=spreads,totals — one request returns the whole available slate
(cost = markets x regions = 2 credits). Prices are discarded in memory; only point values, bookmaker keys and
the provider's update times are written to `data/raw/odds_api/<season>/odds_<stamp>.json` (append-only, git-ignored,
mirrored to the private backup). The API key is read from the environment (loaded from the git-ignored `.env`) and is
never logged, stored or published; every error message is scrubbed of it.

Line-selection rule (documented; applied per game and per snapshot):
  1. Match the API event to the nflverse game by team pair (full name -> abbreviation) and kickoff within 36 h.
  2. Keep a bookmaker only if its spread outcomes name both teams with opposite points (home + away = 0), its total
     has Over and Under at the same point, and both markets were last updated BEFORE kickoff.
  3. home_spread = median of the bookmakers' points for the nflverse HOME team (negative = home favoured, the
     project convention); total = median of the total points; both rounded to the nearest half point.
  4. Needs >= `min_bookmakers` valid bookmakers, a snapshot retrieved before kickoff and before the forecast cutoff,
     and no older than `max_age_hours` at the cutoff. Otherwise the nflverse schedule line (fallback) is used.
  5. Cross-check against the nflverse line for the same game (sign agreement when both are >= 2.5 points from
     pick'em; totals within 10 points); a failed check rejects the API line for that game (fallback).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from statistics import median

import polars as pl
import yaml

from nflcast.config import CONFIG_DIR, RAW_DIR, utc_now, utc_stamp

DIR = RAW_DIR / "odds_api"
STATE = DIR / "state.json"
SOURCE = "the_odds_api"

# The Odds API full team names -> nflverse franchise abbreviations (all 32 teams).
TEAM_ABBR = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL", "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR", "Chicago Bears": "CHI", "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL", "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX", "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC", "Los Angeles Rams": "LA", "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN", "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT", "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB", "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


@lru_cache(maxsize=1)
def cfg() -> dict:
    return yaml.safe_load((CONFIG_DIR / "market_feed.yaml").read_text(encoding="utf-8"))


def feed_version() -> str:
    return cfg()["feed_version"]


def _key() -> str:
    return os.environ.get("ODDS_API_KEY", "").strip()


def _scrub(text: str) -> str:
    k = _key()
    return text.replace(k, "***") if k else text


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


# ------------------------------------------------------------------ state and budget
def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"requests": []}


def _save_state(st: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1), encoding="utf-8")


def _month_end(now: datetime) -> datetime:
    first_next = (now.replace(day=1) + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return first_next


def remaining_credits(st: dict, now: datetime) -> int | None:
    """Last remaining-credit header seen this calendar month (None if unknown or from an earlier month)."""
    last = next((r for r in reversed(st.get("requests", [])) if r.get("requests_remaining") is not None), None)
    if not last or _dt(last["at_utc"]).strftime("%Y-%m") != now.strftime("%Y-%m"):
        return None
    return int(last["requests_remaining"])


def routine_need(now: datetime) -> int:
    """Credits needed for the routine refreshes still to come this month."""
    c = cfg()["odds_api"]
    hours_left = (_month_end(now) - now).total_seconds() / 3600
    return int(hours_left / c["routine_interval_hours"] + 1) * c["cost_per_request"]


def due(now: datetime, next_kickoff: datetime | None, st: dict | None = None) -> tuple[bool, str]:
    """Whether to request now. Missed slots during downtime are never replayed: a request is due only by elapsed time."""
    c, st = cfg()["odds_api"], st if st is not None else load_state()
    if not _key():
        return False, "no API key configured (.env ODDS_API_KEY)"
    reqs = st.get("requests", [])
    last_try = _dt(reqs[-1]["at_utc"]) if reqs else None
    if reqs and not reqs[-1].get("ok") and now - last_try < timedelta(minutes=c["retry_after_error_minutes"]):
        return False, "waiting after a failed request"
    rem = remaining_credits(st, now)
    used_month = sum(r.get("cost") or 0 for r in reqs if r.get("ok") and r["at_utc"][:7] == now.strftime("%Y-%m"))
    if rem is not None and rem < c["hard_floor"]:
        return False, f"quota low ({rem} credits left)"
    if used_month + c["cost_per_request"] > c["monthly_allowance"] - c["safety_reserve"]:
        return False, "monthly allowance reached (own count)"
    last_ok = _dt(st.get("last_success_utc"))
    if last_ok is None or now - last_ok >= timedelta(hours=c["routine_interval_hours"]):
        return True, "routine refresh"
    if (next_kickoff is not None and timedelta(0) < next_kickoff - now <= timedelta(minutes=c["pregame_window_minutes"])
            and now - last_ok >= timedelta(minutes=c["pregame_min_gap_minutes"])):
        if rem is None:
            return False, "pregame refresh skipped (remaining credits unknown)"
        need = routine_need(now) + c["safety_reserve"] + c["cost_per_request"]
        if c.get("pregame_budget_check", True) and rem < need:
            return False, f"pregame refresh skipped (budget: {rem} left, {need} reserved)"
        return True, "pregame refresh"
    return False, "cached (not due)"


# ------------------------------------------------------------------ fetch and sanitise
def sanitize(events: list[dict], retrieved_at: datetime) -> dict:
    """Keep point values only. Every price field is dropped here, before anything is written."""
    out, dropped = [], 0
    for ev in events:
        books = []
        for b in ev.get("bookmakers", []):
            m = {mk["key"]: mk for mk in b.get("markets", [])}
            sp, to = m.get("spreads"), m.get("totals")
            if not sp or not to:
                dropped += 1
                continue
            pts = {o.get("name"): o.get("point") for o in sp.get("outcomes", [])}
            tot = {o.get("name"): o.get("point") for o in to.get("outcomes", [])}
            books.append({"bookmaker": b.get("key"), "bookmaker_last_update": b.get("last_update"),
                          "spread_updated": sp.get("last_update"), "total_updated": to.get("last_update"),
                          "home_point": pts.get(ev.get("home_team")), "away_point": pts.get(ev.get("away_team")),
                          "over_point": tot.get("Over"), "under_point": tot.get("Under")})
        out.append({"event_id": ev.get("id"), "commence_time": ev.get("commence_time"),
                    "home_team": ev.get("home_team"), "away_team": ev.get("away_team"), "books": books})
    return {"source": SOURCE, "retrieved_at_utc": retrieved_at.isoformat(), "request": {
        "endpoint": cfg()["odds_api"]["endpoint"], "regions": cfg()["odds_api"]["regions"],
        "markets": cfg()["odds_api"]["markets"]}, "note": "Point values only; all prices discarded before saving.",
        "books_without_both_markets": dropped, "events": out}


def fetch(now: datetime | None = None, reason: str = "manual") -> dict:
    """One request for the whole slate. Returns a summary (never the key). Records credit headers in state."""
    import requests
    now = now or utc_now()
    c, st = cfg()["odds_api"], load_state()
    rec = {"at_utc": now.isoformat(), "reason": reason, "ok": False}
    try:
        r = requests.get(c["endpoint"], timeout=30, params={
            "apiKey": _key(), "regions": c["regions"], "markets": c["markets"], "oddsFormat": "american", "dateFormat": "iso"})
        rec.update({"http_status": r.status_code, "requests_remaining": _int(r.headers.get("x-requests-remaining")),
                    "requests_used": _int(r.headers.get("x-requests-used")), "cost": _int(r.headers.get("x-requests-last"))})
        if r.status_code != 200:
            rec["error"] = _scrub(r.text[:200])
        else:
            snap = sanitize(r.json(), now)
            path = DIR / str(now.year) / f"odds_{utc_stamp(now)}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(snap, indent=1), encoding="utf-8")
            rec.update({"ok": True, "events": len(snap["events"]), "file": path.name})
            st["last_success_utc"] = now.isoformat()
    except Exception as e:  # noqa: BLE001 - network problems fall back to nflverse; the message is scrubbed of the key
        rec["error"] = _scrub(f"{type(e).__name__}: {e}")[:300]
    st.setdefault("requests", []).append(rec)
    _save_state(st)
    return rec


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def refresh_if_due(now: datetime, next_kickoff: datetime | None) -> dict:
    ok, why = due(now, next_kickoff)
    if not ok:
        return {"fetched": False, "reason": why, "requests_remaining": remaining_credits(load_state(), now)}
    rec = fetch(now, reason=why)
    return {"fetched": rec["ok"], "reason": why, "requests_remaining": rec.get("requests_remaining"),
            "events": rec.get("events"), "cost": rec.get("cost"), "error": rec.get("error")}


# ------------------------------------------------------------------ consensus lines
def _half(x: float) -> float:
    return round(x * 2) / 2


def consensus(event: dict, home_abbr: str, kickoff: datetime, min_books: int) -> dict | None:
    """Median point spread (for the nflverse home team) and total from valid pre-kickoff bookmakers."""
    api_home = TEAM_ABBR.get(event["home_team"])
    flip = api_home != home_abbr        # API lists the teams the other way round (e.g. neutral site)
    hs, tot, upd, books = [], [], [], []
    for b in event["books"]:
        h, a, ov, un = b["home_point"], b["away_point"], b["over_point"], b["under_point"]
        if None in (h, a, ov, un) or abs(h + a) > 1e-9 or ov != un:
            continue
        times = [_dt(b["spread_updated"] or b["bookmaker_last_update"]), _dt(b["total_updated"] or b["bookmaker_last_update"])]
        if any(t is None or t >= kickoff for t in times):
            continue
        hs.append(float(a if flip else h))
        tot.append(float(ov))
        upd += times
        books.append(b["bookmaker"])
    if len(books) < min_books:
        return None
    return {"home_spread": _half(median(hs)), "total": _half(median(tot)), "n_books": len(books),
            "bookmakers": sorted(books), "provider_updated_at": max(upd), "provider_updated_earliest": min(upd),
            "teams_reversed_in_api": flip}


def market_rows(games: pl.DataFrame) -> pl.DataFrame:
    """One row per (API snapshot, matched nflverse game) with the consensus line. Columns follow market_asof."""
    c = cfg()["odds_api"]
    sched = games.select("game_id", "home_id", "away_id", "kickoff_utc").to_dicts()
    rows = []
    for f in sorted(DIR.glob("*/odds_*.json")):
        snap = json.loads(f.read_text(encoding="utf-8"))
        got = _dt(snap["retrieved_at_utc"])
        for ev in snap["events"]:
            h, a = TEAM_ABBR.get(ev["home_team"]), TEAM_ABBR.get(ev["away_team"])
            start = _dt(ev["commence_time"])
            if not h or not a or start is None:
                continue
            match = [g for g in sched if {g["home_id"], g["away_id"]} == {h, a}
                     and abs((g["kickoff_utc"] - start).total_seconds()) <= 36 * 3600]
            if len(match) != 1:
                continue
            g = match[0]
            ko = min(g["kickoff_utc"], start)
            if got >= ko:
                continue          # never a snapshot taken at/after kickoff
            cons = consensus(ev, g["home_id"], ko, c["min_bookmakers"])
            if cons is None:
                continue
            rows.append({"game_id": g["game_id"], "snapshot_at": got, "home_spread": cons["home_spread"],
                         "total": cons["total"], "market_source": SOURCE, "market_timing": "timestamped",
                         "provider_updated_at": cons["provider_updated_at"], "n_books": cons["n_books"],
                         "teams_reversed_in_api": cons["teams_reversed_in_api"]})
    if not rows:
        return pl.DataFrame()
    return pl.DataFrame(rows).with_columns(pl.col("snapshot_at").dt.cast_time_unit("us"),
                                           pl.col("provider_updated_at").dt.cast_time_unit("us"))


def cross_check_ok(api_hs: float, api_total: float, nfl_hs: float | None, nfl_total: float | None) -> bool:
    """Team/sign sanity check against the nflverse line for the same game (if one exists)."""
    if nfl_hs is None or nfl_total is None:
        return True
    if abs(api_hs) >= 2.5 and abs(nfl_hs) >= 2.5 and (api_hs > 0) != (nfl_hs > 0):
        return False
    return abs(api_total - nfl_total) <= 10


def status(now: datetime) -> dict:
    """Public-safe feed status (no key, no credits)."""
    st = load_state()
    return {"feed_version": feed_version(), "key_configured": bool(_key()), "last_success_utc": st.get("last_success_utc")}
