"""Prospective operation. Safe to run on a timer (every 30 minutes).

Each run: refresh current-season snapshots -> rebuild processed tables -> score finished games ->
update publication evidence -> build a CANDIDATE release in memory -> publish it only if due ->
re-export the website data -> commit/push published outputs -> rebuild the local static site.

A candidate is published when, for any unplayed game of the upcoming week:
  * the game has no valid forecast yet, or its latest valid version predates input fingerprints;
  * any input fingerprint changed versus that game's latest valid version: market spread/total,
    quarterback availability (statuses, evidence, scenarios, overrides), injury report (displayed),
    team form (new completed games), or the model/code version;
  * the game kicks off within `final_window_min` minutes and no release has been made since that
    window opened (final-pregame version); or
  * no release has been made for `daily_hours` (heartbeat, which also provides >=72 h early versions).
Games that have kicked off are never included in a new release, so pregame forecasts stop updating at
kickoff. Every earlier version is preserved (releases are write-once).
"""

from __future__ import annotations

import json
import subprocess
import time
import traceback
from datetime import datetime, timedelta

from nflcast.config import RELEASES_DIR, ROOT, release_paths, utc_now
from nflcast.predict.validation import entry_is_valid

LOG = ROOT / "logs" / "operate.log"
FINGERPRINT_KEYS = ("market", "quarterbacks", "injury_report", "team_form", "model")


def _log(msg: str) -> None:
    LOG.parent.mkdir(exist_ok=True)
    line = f"{utc_now().isoformat(timespec='seconds')} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def published_versions() -> tuple[dict[str, tuple[datetime, dict]], datetime | None]:
    """Latest VALID pregame version per game, and the time of the latest schema-v2+ release."""
    latest: dict[str, tuple[datetime, dict]] = {}
    last_release = None
    for f in release_paths():
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("schema_version", 1) < 2:
            continue
        gen = datetime.fromisoformat(r["generated_at_utc"])
        last_release = max(last_release, gen) if last_release else gen
        for g in r["games"]:
            if not entry_is_valid(g) or gen >= datetime.fromisoformat(g["kickoff_utc"]):
                continue
            if g["game_id"] not in latest or gen > latest[g["game_id"]][0]:
                latest[g["game_id"]] = (gen, g)
    return latest, last_release


def decide(candidate: dict, now: datetime, latest: dict, last_release: datetime | None,
           daily_hours: float = 20, final_window_min: int = 60) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for g in candidate["games"]:
        gid, ko = g["game_id"], datetime.fromisoformat(g["kickoff_utc"])
        if ko <= now:
            continue
        prev = latest.get(gid)
        if prev is None:
            reasons.append(f"{gid}: no valid forecast yet")
            continue
        prev_fp = prev[1].get("input_fingerprint")
        if not prev_fp:
            reasons.append(f"{gid}: previous version has no input fingerprint (schema upgrade)")
            continue
        changed = [k for k in FINGERPRINT_KEYS if prev_fp.get(k) != g["input_fingerprint"].get(k)]
        if changed:
            reasons.append(f"{gid}: changed {', '.join(changed)}")
        if ko - now <= timedelta(minutes=final_window_min) and prev[0] < ko - timedelta(minutes=final_window_min):
            reasons.append(f"{gid}: final-pregame window")
    if last_release is None or now - last_release >= timedelta(hours=daily_hours):
        reasons.append("routine heartbeat")
    return bool(reasons), reasons


def _odds_refresh() -> str:
    """The Odds API refresh when due (routine every 6 h / budgeted pregame). Returns a log line without the key."""
    import polars as pl

    from nflcast.config import PROCESSED_DIR
    from nflcast.data import odds_api as OA
    now = utc_now()
    g = pl.read_parquet(PROCESSED_DIR / "games.parquet").filter(
        (pl.col("status") == "scheduled") & (pl.col("kickoff_utc") > now))
    nxt = g["kickoff_utc"].min() if g.height else None
    r = OA.refresh_if_due(now, nxt)
    return (f"fetched={r['fetched']} reason={r['reason']} events={r.get('events')} cost={r.get('cost')} "
            f"credits_remaining={r.get('requests_remaining')}{' error=' + r['error'] if r.get('error') else ''}")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


PUBLISH_TRIGGERS = ["releases", "reports/prospective"]
PUBLISH_PATHS = PUBLISH_TRIGGERS + ["web/public/data"]


def publish(note: str) -> bool:
    """Commit and push published outputs, only when a release, evidence, correction or scored result changed."""
    if _git("remote", "get-url", "origin").returncode != 0:
        _log("publish: no git remote 'origin'; skipped")
        return False
    if not _git("status", "--porcelain", "--", *PUBLISH_TRIGGERS).stdout.strip():
        _log("publish: no new release, evidence or results; nothing pushed")
        return False
    _git("add", "--", *PUBLISH_PATHS)
    c = _git("commit", "-m", f"Publish: {note}")
    if c.returncode != 0:
        _log(f"publish: commit failed: {c.stderr.strip()[:500]}")
        return False
    p = _git("push", "origin", "HEAD:main")
    _log(f"publish: push exit={p.returncode} {p.stderr.strip()[-300:]}")
    return p.returncode == 0


def run(build_site: bool = True, force: bool = False) -> None:
    from nflcast import pipeline
    from nflcast.predict import archive, export_web, publication, release, score

    _log("operate: start")
    try:
        offline_since = _last_done()
    except Exception:  # noqa: BLE001 - alerts never block a cycle
        offline_since = None
    problems = archive.verify()
    missing_only = all(p.startswith("no manifest") for p in problems)
    if problems and not missing_only:
        _log("operate: INTEGRITY VIOLATION, publishing stopped: " + "; ".join(problems))
        _alert_failure("integrity", "Archived forecast files changed; publishing is stopped. Ask Claude to investigate.")
        raise RuntimeError("archived forecast files changed: " + "; ".join(problems))
    from nflcast.predict import freeze
    fz = freeze.check()
    if fz:
        _log("operate: MODEL FREEZE VIOLATION, publishing stopped: " + "; ".join(fz))
        _alert_failure("freeze", "The frozen model or its settings changed; publishing is stopped. Ask Claude to investigate.")
        raise RuntimeError("model freeze violated: " + "; ".join(fz))
    try:
        pipeline.ingest()
        pipeline.build()
        try:
            _log("operate: odds " + _odds_refresh())
        except Exception as e:  # noqa: BLE001 - the market feed is best-effort; nflverse lines are the fallback
            from nflcast.data.odds_api import _scrub
            _log(f"operate: odds refresh failed: {_scrub(str(e))[:300]}")
        try:
            from nflcast.predict.collect import collect
            c = collect()
            _log(f"operate: collected weather snapshots={c['weather_snapshots_written']}, "
                 f"injury versions={c['injury_versions']['player_week_versions']}")
        except Exception as e:  # noqa: BLE001 - collection is best-effort and never blocks forecasting
            _log(f"operate: collection failed: {e}")
        try:
            from nflcast.predict import backup
            b = backup.sync()
            _log(f"operate: backup ok={b.get('ok')} copied={b.get('files_copied')} pushed={b.get('pushed')} {b.get('error') or b.get('push_error') or ''}")
        except Exception as e:  # noqa: BLE001 - backup is best-effort and never blocks forecasting
            _log(f"operate: backup failed: {e}")
        score.score()
        try:
            publication.update_evidence()
            n = publication.record_late_publications()
            if n:
                _log(f"operate: recorded {n} late-publication correction(s)")
        except Exception as e:  # noqa: BLE001 - evidence is best-effort; never blocks forecasting
            _log(f"operate: publication evidence update failed: {e}")
        now = utc_now()
        cand = release.build_candidate(now=now)
        released, pushed = None, None
        if cand is None:
            _log(f"operate: no release: {release.last_skip_reason or 'no upcoming games in window'}")
        else:
            latest, last_release = published_versions()
            due, reasons = (True, ["forced"]) if force else decide(cand, now, latest, last_release)
            _log(f"operate: release due={due} ({'; '.join(reasons[:8])}{' ...' if len(reasons) > 8 else ''})")
            if due:
                bad = [g["game_id"] for g in cand["games"] if not entry_is_valid(g)]
                if bad:
                    _log(f"operate: {len(bad)} game(s) failed validation and stay on their last valid version: {bad}")
                path = release.write_release(cand)
                archive.create_manifest(path)
                ts = archive.timestamp(path)
                _log(f"operate: release {path}; archived (sha256 manifest; trusted timestamp {'ok' if ts else 'pending retry'})")
                released = sum(entry_is_valid(g) for g in cand["games"])
        export_web.export()
        pushed = publish(f"{utc_now().isoformat(timespec='minutes')}")
        if pushed:
            for _ in range(6):  # give GitHub a moment to register the push run, then record evidence
                time.sleep(10)
                before = json.dumps(publication.load_evidence(), sort_keys=True)
                if json.dumps(publication.update_evidence(), sort_keys=True) != before:
                    publication.record_late_publications()
                    a = archive.run(capture_public=True)
                    _log(f"operate: archive {a}")
                    export_web.export()
                    publish("publication evidence and archive records")
                    break
        else:
            a = archive.run(capture_public=True)   # retries any pending timestamps/captures; appends only
            if any(a[k] for k in ("manifests", "timestamps", "github_runs", "web_archive")):
                _log(f"operate: archive {a}")
                export_web.export()
                publish("archive records")
        _alerts(cand, now)
        if build_site:
            r = subprocess.run("npx next build", cwd=ROOT / "web", shell=True, capture_output=True, text=True)
            _log(f"operate: site build exit={r.returncode}")
            if r.returncode != 0:
                _log(r.stdout[-2000:] + r.stderr[-2000:])
    except Exception:  # noqa: BLE001 - log everything, keep the last good release live
        _log("operate: FAILED\n" + traceback.format_exc())
        _alert_failure("error", "A scheduled run failed; the site keeps the last published forecasts. See logs/operate.log or ask Claude.")
        raise
    _caught_up_notice(offline_since, released, pushed)
    _log("operate: done")


def _last_done():
    from nflcast.predict import alerts as AL
    return AL.last_completed_run(LOG)


def _alerts(cand, now) -> None:
    """Desktop alerts for items needing a human (best effort; never blocks forecasting)."""
    try:
        from nflcast.predict import alerts as AL
        items = AL.attention_items(cand, now)
        try:
            from nflcast.data import odds_api as OA
            items += AL.credit_items(OA.remaining_credits(OA.load_state(), now))
        except Exception as e:  # noqa: BLE001 - a bad credit log must not hide game alerts
            _log(f"operate: credit check failed: {e}")
        shown = AL.notify(items, now)
        _log(f"operate: alerts open={len(items)} shown={len(shown)}")
    except Exception as e:  # noqa: BLE001
        _log(f"operate: alerts failed: {e}")


def _alert_failure(kind: str, text: str) -> None:
    """One key per failure kind, so a serious failure is never hidden behind an earlier generic one."""
    try:
        from nflcast.predict import alerts as AL
        AL.notify([{"key": f"run_failed:{kind}", "game_id": None, "url": AL.SITE, "text": text}], forget_resolved=False)
    except Exception:  # noqa: BLE001
        pass


def _caught_up_notice(offline_since, released, pushed) -> None:
    """After >= 6 h without a completed run (PC off/asleep, or failed runs), say what this cycle actually did."""
    try:
        from nflcast.predict import alerts as AL
        if offline_since is None:
            return
        gap = (utc_now() - offline_since).total_seconds() / 3600
        if gap < 6:
            return
        title, body = AL.caught_up_text(gap, released, pushed)
        ok = AL.toast(title, body, AL.SITE)
        _log(f"operate: caught-up notice ({gap:.1f} h since last completed run) {'shown' if ok else 'NOT SHOWN'}")
    except Exception as e:  # noqa: BLE001
        _log(f"operate: caught-up notice failed: {e}")
