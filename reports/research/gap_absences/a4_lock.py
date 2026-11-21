"""A4 (proposal only): a 2027 lock rule that waits for final injury statuses, and its cost in line movement.

Candidate rule "lock-final-status": the lock-24h version if both teams' final game designations were already in our data
at kickoff - 24 h; otherwise the earliest valid version with a line generated at or after the time both teams' final
designations were first in our data, but never later than kickoff - 3 h (if none, the latest valid lined version at or
before kickoff - 3 h).
For every 2026 lock-24h game (weeks 7-11) this replays the archived releases and compares the line at the actual lock
with the line at the candidate lock: size of the move, and whether it moved toward the stats-only side (which makes the
later lock "cost" that movement). Lines only, no results. Writes a4_lock.json.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import polars as pl  # noqa: E402

from common import OUT, releases, save  # noqa: E402
from nflcast.predict.validation import entry_is_valid  # noqa: E402

T = pl.read_parquet(OUT / "a1_timing.parquet").filter(pl.col("rule") == "lock-24h")
rows = []
for gid, d in T.group_by("game_id"):
    gid = gid[0]
    ko = d["kickoff_utc"][0]
    arrive = d["designations_first_seen"].max()
    start = max(ko - timedelta(hours=24), arrive) if arrive is not None else ko - timedelta(hours=24)
    cap = ko - timedelta(hours=3)
    vers = [(r["generated_at"], r["games"][gid]) for r in releases() if gid in r["games"] and r["generated_at"] < ko
            and entry_is_valid(r["games"][gid]) and (r["games"][gid].get("market") or {}).get("home_spread") is not None]
    vers.sort(key=lambda x: x[0])
    lock_at = d["lock_at"][0]
    actual = next(v for t, v in vers if t == lock_at) if any(t == lock_at for t, _ in vers) else None
    inwin = [x for x in vers if start <= x[0] <= cap]
    if arrive is not None and arrive <= ko - timedelta(hours=24):
        cand = (lock_at, None)
        inwin = True
    else:
        cand = inwin[0] if inwin else ([x for x in vers if x[0] <= cap] or [None])[-1]
    if actual is None or cand is None:
        continue
    cand = (cand[0], cand[1] if cand[1] is not None else actual)
    l0, l1 = actual["market"]["home_spread"], cand[1]["market"]["home_spread"]
    so = actual.get("football_only") or {}
    gap = (so.get("margin") or 0) + l0                 # >0: stats-only line above the market for home
    rows.append({"game_id": gid, "slot": d["slot"][0], "lock_at": lock_at, "candidate_at": cand[0],
                 "hours_later": (cand[0] - lock_at).total_seconds() / 3600, "line_lock": l0, "line_candidate": l1,
                 "move_home": l1 - l0, "toward_stats_side": (-(l1 - l0)) * (1 if gap > 0 else -1) if gap != 0 else 0.0,
                 "big_gap": abs(gap) >= 3, "same_version": cand[0] == lock_at, "statuses_in_window": bool(inwin)})
R = pl.DataFrame(rows)


def summ(d):
    return {"n": d.height, "changed_version": int((~d["same_version"]).sum()), "median_hours_later": float(d["hours_later"].median()),
            "lines_moved": int((d["move_home"] != 0).sum()), "mean_abs_move": float(d["move_home"].abs().mean()),
            "mean_toward_stats_side": float(d["toward_stats_side"].mean())}


res = {"rule": "lock-24h version if both teams' final designations were in our data by then; otherwise the earliest valid "
               "lined version after they arrive, capped at kickoff-3h", "all": summ(R), "big_gaps": summ(R.filter(pl.col("big_gap"))),
       "by_slot": {s[0]: summ(d) for s, d in R.group_by(["slot"])}, "games": R.sort("lock_at").to_dicts()}
save("a4_lock", res)
print({k: v for k, v in res.items() if k != "games"})
