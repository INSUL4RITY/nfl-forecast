"""Desktop alerts: things that need a human before kickoff (Windows toast notifications; logged to logs/alerts.log).

Checked on every scheduled cycle against the freshly built candidate (the latest inputs), for games kicking off within
48 hours:
  * no quarterback could be identified for a team, or the game has no valid new forecast;
  * a team's injury report is not current within 36 h of kickoff, or game designations are still pending within 24 h
    (skipped while a documented QB override for that team is in effect; one combined item if many teams are affected);
  * a QB listed Out on the official report had to be kept out although the report could not be re-confirmed;
  * the leading QB is below 90% to start (names and probabilities in the alert);
  * no market line within 24 h of kickoff;
plus: The Odds API credits low, failed or blocked cycles, and a "caught up" notice after >= 6 h without a completed run.
Each issue has a stable key. It alerts when new, again when its content changes (at most every CHANGE_HOURS) or when still
open after RESEND_HOURS, and is forgotten only after being absent for FORGET_HOURS. Only toasts that were actually shown
count as sent; failed ones are retried (up to MAX_TRIES per RESEND_HOURS). One toast per cycle summarises the due items;
clicking it opens the first game's page. Alerts never change any forecast, release or published file.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timedelta

from nflcast.config import ROOT, utc_now

LOG = ROOT / "logs" / "alerts.log"
STATE = ROOT / "logs" / "alerts_state.json"
SITE = "https://insul4rity.github.io/nfl-forecast"
WINDOW_HOURS, REPORT_HOURS, PENDING_HOURS, LINE_HOURS = 48, 36, 24, 24
LEAD_QB_MIN = 0.90
FEED_WIDE_TEAMS = 6
CREDITS_LOW = 60
RESEND_HOURS, CHANGE_HOURS, FORGET_HOURS, MAX_TRIES = 12, 2, 1, 3


def _pct(p: float) -> str:
    return f"{p * 100:.0f}%" if 0.01 <= p <= 0.99 else f"{p * 100:.1f}%"


def _item(key: str, text: str, gid: str | None, content: str = "") -> dict:
    """`content` is what counts as a change for re-alerting (e.g. the QB split) -- never the countdown in `text`."""
    return {"key": key, "text": text, "game_id": gid, "url": f"{SITE}/game/{gid}/" if gid else SITE, "content": content}


def _game_items(g: dict, now: datetime) -> tuple[list[dict], list[tuple[str, str, float]]]:
    """Items for one game, plus (team, game_id, hours) report problems for feed-wide aggregation."""
    items, report_issues = [], []
    ko = datetime.fromisoformat(g["kickoff_utc"])
    h = (ko - now).total_seconds() / 3600
    if h <= 0 or h > WINDOW_HOURS:
        return items, report_issues
    gid, when = g["game_id"], f"kickoff in {h:.0f} h"
    if g.get("status") == "rejected_validation_failed":
        items.append(_item(f"{gid}:no_valid_forecast", f"{g['away_team']} @ {g['home_team']}: the new forecast failed its checks "
                           f"({when}); the site keeps the previous version. Ask Claude to look.", gid))
    for side in ("away", "home"):
        L = g["lineup"][side]
        team, flags = L.get("team") or g[f"{side}_team"], set(L.get("flags") or [])
        scen = L.get("scenarios") or []
        overridden = bool(L.get("overrides_used"))
        if flags & {"no_candidate_qb", "no_available_qb", "no_candidate_qb_prior_used"} or (scen and scen[0].get("qb") is None):
            items.append(_item(f"{gid}:{team}:no_qb", f"{team}: no starting QB could be identified ({when}); the forecast uses "
                               "a generic QB. Send a source for the starter.", gid))
        if "listed_out_despite_stale_report" in flags:
            items.append(_item(f"{gid}:{team}:out_kept", f"{team}: injury data could not be re-confirmed ({when}); the QB listed "
                               "Out is kept out. Check the latest report.", gid))
        if not overridden:
            if flags & {"report_stale", "report_not_available"} and h <= REPORT_HOURS:
                report_issues.append((team, gid, h))
            elif "designation_pending" in flags and h <= PENDING_HOURS:
                items.append(_item(f"{gid}:{team}:designation_pending", f"{team}: game designations still not published "
                                   f"({when}). Check the news.", gid))
        if scen and scen[0].get("qb") is not None and scen[0]["p"] < LEAD_QB_MIN:
            who = ", ".join(f"{s['qb'] or 'unknown'} {_pct(s['p'])}" for s in scen[:3])
            items.append(_item(f"{gid}:{team}:qb_uncertain", f"{team} starting QB uncertain ({when}): {who}. Send a source "
                               "if there is news.", gid, content=who))
    if g.get("market") is None and h <= LINE_HOURS and g.get("status") != "rejected_validation_failed":
        items.append(_item(f"{gid}:no_line", f"{g['away_team']} @ {g['home_team']}: no market line ({when}); the "
                           "football-only forecast is used.", gid))
    return items, report_issues


def attention_items(candidate: dict | None, now: datetime) -> list[dict]:
    """What needs a human, from a candidate release (in-memory; nothing is written). One bad game never hides the rest."""
    items, reports = [], []
    for g in (candidate or {}).get("games", []):
        try:
            gi, gr = _game_items(g, now)
        except Exception:  # noqa: BLE001 - a malformed entry must not drop the other games' alerts
            gi, gr = [_item(f"{g.get('game_id')}:unreadable", f"{g.get('game_id')}: forecast entry could not be checked; "
                            "ask Claude to look.", g.get("game_id"))], []
        items += gi
        reports += gr
    if len(reports) >= FEED_WIDE_TEAMS:        # one root cause (feed not current) -> one item, not one per team
        items.append(_item("injury_feed_not_current", f"Injury reports not current for {len(reports)} teams playing within "
                           f"{REPORT_HOURS} h; QB availability uses historical rates. The feed may be late.", reports[0][1],
                           content=str(len(reports))))
    else:
        items += [_item(f"{gid}:{team}:no_current_report", f"{team}: no current injury report (kickoff in {h:.0f} h); QB "
                        "availability uses historical rates. If the starter is known, send a source.", gid) for team, gid, h in reports]
    return items


def credit_items(credits_remaining: int | None) -> list[dict]:
    if credits_remaining is not None and credits_remaining < CREDITS_LOW:
        return [_item("odds_credits_low", f"The Odds API credits low ({credits_remaining} left this month); nflverse lines "
                      "are used when it runs out.", None, content=str(credits_remaining // 20))]
    return []


def _aware(s) -> datetime | None:
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else None
    except (TypeError, ValueError):
        return None


def _load_state() -> dict:
    """Remembered items; anything malformed is dropped (a bad file can never silence alerts)."""
    try:
        raw = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    for k, v in raw.items():
        if isinstance(v, dict) and _aware(v.get("last_seen")):
            out[k] = v
    return out


def toast(title: str, body: str, url: str = "") -> bool:
    """Show a Windows toast via scripts/toast.ps1. True only if Windows accepted it (never raises)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "scripts" / "toast.ps1"),
                            "-Title", title, "-Body", body, "-Url", url], capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except Exception:  # noqa: BLE001 - alerts are best-effort
        return False


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def notify(items: list[dict], now: datetime | None = None, send=None, forget_resolved: bool = True) -> list[dict]:
    """Send ONE toast for the due items. Returns the items actually shown (empty if nothing was due or the toast failed).
    forget_resolved: forget remembered items absent for FORGET_HOURS (a full cycle's view); False for one-off alerts."""
    send = send or toast
    now = now or utc_now()
    state = _load_state()
    due = []
    for i in items:
        s = state.get(i["key"])
        sent, last_try = _aware((s or {}).get("sent")), _aware((s or {}).get("last_try"))
        changed = s is not None and s.get("digest") != _digest(i.get("content", ""))
        if s is None or sent is None:
            is_due = s is None or (s.get("tries", 0) < MAX_TRIES) or (last_try and now - last_try >= timedelta(hours=RESEND_HOURS))
        else:
            is_due = now - sent >= timedelta(hours=RESEND_HOURS) or (changed and now - sent >= timedelta(hours=CHANGE_HOURS))
        if is_due:
            due.append(i)
        state[i["key"]] = {**(s or {}), "last_seen": now.isoformat()}
    shown = False
    if due:
        title = "NFL Forecast: 1 item needs a look" if len(due) == 1 else f"NFL Forecast: {len(due)} items need a look"
        body = "\n".join(i["text"] for i in due[:3]) + (f"\n+{len(due) - 3} more (see logs/alerts.log)" if len(due) > 3 else "")
        shown = bool(send(title, body, next((i["url"] for i in due if i.get("game_id")), due[0]["url"])))
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            for i in due:
                fh.write(f"{now.isoformat(timespec='seconds')} {'shown' if shown else 'NOT SHOWN'} {i['text']}\n")
        for i in due:
            s = state[i["key"]]
            if shown:
                state[i["key"]] = {"sent": now.isoformat(), "digest": _digest(i.get("content", "")), "last_seen": now.isoformat()}
            else:
                state[i["key"]] = {**s, "tries": s.get("tries", 0) + 1, "last_try": now.isoformat()}
    if forget_resolved:
        state = {k: v for k, v in state.items()
                 if now - _aware(v["last_seen"]) < timedelta(hours=FORGET_HOURS) or k in {i["key"] for i in items}}
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    return due if shown else []


def last_completed_run(log_path=None) -> datetime | None:
    """Time of the last successful cycle ('operate: done') in logs/operate.log."""
    p = log_path or ROOT / "logs" / "operate.log"
    try:
        for line in reversed(p.read_text(encoding="utf-8").splitlines()):
            if line.endswith("operate: done"):
                return _aware(line.split(" ", 1)[0])
    except OSError:
        return None
    return None


def caught_up_text(gap_hours: float, valid_games: int | None, pushed: bool | None) -> tuple[str, str]:
    """Title/body for the notice after >= 6 h without a completed run; states only what actually happened."""
    title = f"NFL Forecast caught up ({gap_hours:.0f} h since the last completed run)"
    body = "Refreshed injuries, depth charts, market lines and results. "
    if not valid_games:
        body += "No forecast inputs had changed."
    elif pushed:
        body += f"New forecast for {valid_games} game(s) published to the site."
    else:
        body += f"New forecast for {valid_games} game(s) saved locally, but the upload to the site failed; it will retry."
    return title, body
