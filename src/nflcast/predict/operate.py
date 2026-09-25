"""Milestone 7: prospective operation. Safe to run on a timer (e.g. every 30 minutes).

Each run: refresh current-season snapshots -> rebuild processed tables -> score finished games ->
publish a release only if one is due -> re-export the website data (and rebuild the static site).

A release is due when either
  * no release has been generated in the last `daily_hours` (the routine early/update release), or
  * an unplayed game kicks off within the next `final_window_min` minutes and no release has been
    generated since `final_window_min` minutes before that kickoff (the final-pregame release).
Deciding from the live schedule means kickoff-time and daylight-saving changes need no manual edits.
Every step is logged to logs/operate.log; failures are logged and the previous release stays live.
"""

from __future__ import annotations

import json
import subprocess
import traceback
from datetime import datetime, timedelta

import polars as pl

from nflcast.config import RELEASES_DIR, ROOT, utc_now
from nflcast.data import sources as S
from nflcast.data.games import build_games

LOG = ROOT / "logs" / "operate.log"


def _log(msg: str) -> None:
    LOG.parent.mkdir(exist_ok=True)
    line = f"{utc_now().isoformat(timespec='seconds')} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _last_release_time() -> datetime | None:
    files = sorted(RELEASES_DIR.rglob("rel_*.json"))
    for f in reversed(files):
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("schema_version", 1) >= 2:
            return datetime.fromisoformat(r["generated_at_utc"])
    return None


def release_due(now: datetime, daily_hours: float = 20, final_window_min: int = 60) -> tuple[bool, str]:
    games = build_games(S.fetch("schedules"))
    last = _last_release_time()
    soon = games.filter((pl.col("status") == "scheduled") & (pl.col("kickoff_utc") > now)
                        & (pl.col("kickoff_utc") <= now + timedelta(minutes=final_window_min)))
    if soon.height:
        window_start = soon["kickoff_utc"].min() - timedelta(minutes=final_window_min)
        if last is None or last < window_start:
            return True, f"final-pregame window for {soon.height} game(s)"
    upcoming = games.filter((pl.col("status") == "scheduled") & (pl.col("kickoff_utc") > now)
                            & (pl.col("kickoff_utc") <= now + timedelta(days=8)))
    if upcoming.height and (last is None or now - last >= timedelta(hours=daily_hours)):
        return True, "routine daily release"
    return False, "not due"


def run(build_site: bool = True, force: bool = False) -> None:
    from nflcast import pipeline
    from nflcast.predict import export_web, release, score

    _log("operate: start")
    try:
        pipeline.ingest()
        pipeline.build()
        score.score()
        now = utc_now()
        due, why = (True, "forced") if force else release_due(now)
        _log(f"operate: release due={due} ({why})")
        if due:
            path = release.generate(now=now)
            _log(f"operate: release {path}")
        export_web.export()
        if build_site:
            r = subprocess.run("npx next build", cwd=ROOT / "web", shell=True, capture_output=True, text=True)
            _log(f"operate: site build exit={r.returncode}")
            if r.returncode != 0:
                _log(r.stdout[-2000:] + r.stderr[-2000:])
    except Exception:  # noqa: BLE001 - log everything, keep the last good release live
        _log("operate: FAILED\n" + traceback.format_exc())
        raise
    _log("operate: done")
