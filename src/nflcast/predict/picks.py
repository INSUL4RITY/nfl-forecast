"""Model picks and weekly results (display/reporting only; no model change).

A pick is derived from ONE forecast version and the market line archived IN THAT SAME version:
  * winner pick: the team with the higher win probability (exactly equal = toss-up, no pick);
  * projected winning margin: |projected margin|;
  * spread lean ("margin comparison"): d = projected margin - line margin, where line margin = -home_spread (the
    home team's expected margin implied by the line; project convention home_spread < 0 = home favoured).
    d > 0 leans to the home side of the line, d < 0 to the away side; |d| < NO_LEAN (displays as 0.00) = "No lean".
    The size of |d| is labelled so a tiny difference is never presented as a strong prediction.
Which version's spread pick is shown and graded (the "locked pick") depends on the rule in force for the game:
  * "original-pick" (user decision 2026-10-01; games kicking off from RULE_START on, i.e. week 4 onward): the
    earliest valid version generated before kickoff that has a market line, graded against the line archived in that
    same version, so later line moves and forecasts never change it (BUF opens -7.5 with BUF projected by 6.4: the
    pick stays "opponent +7.5" even if the line closes -6.0);
  * "final-pregame" (games before RULE_START; the rule in force when they were played, so finished weeks are never
    regraded): the final_pregame version (latest valid version generated before kickoff) with its own line.
  The PROJECTED WINNER and the margin error always use the final_pregame version, as scoring does.
Actual ties, pushes, no-lean and no-line cases are counted separately. Releases generated from picks-v1 on store the
pick of each version (unchanged); for older versions the same labelling rule is applied now and the pick is flagged
`retrospectively_derived`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from nflcast.predict.validation import entry_is_valid, select_frozen

PICKS_VERSION = "picks-v1"          # labelling rule stored in each release (unchanged)
RULE_START = datetime(2026, 10, 1, tzinfo=timezone.utc)   # "original-pick" for games kicking off from here on
NO_LEAN = 0.005          # points; below this the difference displays as 0.00


def strength(abs_d: float) -> str:
    if abs_d < NO_LEAN:
        return "none"
    if abs_d < 0.5:
        return "tiny"
    if abs_d < 1.5:
        return "small"
    if abs_d < 3.0:
        return "moderate"
    return "large"


def derive(forecast: dict | None, market: dict | None, home: str, away: str) -> dict | None:
    """Pick labels from one forecast and the market line recorded with it (None if no forecast)."""
    if not forecast:
        return None
    m, ph, pa = float(forecast["margin"]), float(forecast["p_home"]), float(forecast["p_away"])
    winner = home if ph > pa else away if pa > ph else None
    out = {"picks_version": PICKS_VERSION, "winner": winner, "winner_p": max(ph, pa) if winner else None,
           "projected_margin": m, "winning_margin": abs(m), "line_home_spread": None, "lean": None}
    if not market or market.get("home_spread") is None:
        out["lean"] = {"side": None, "status": "no_line"}
        return out
    hs = float(market["home_spread"])
    d = m - (-hs)
    out["line_home_spread"] = hs
    if abs(d) < NO_LEAN:
        out["lean"] = {"side": None, "status": "no_lean", "difference": 0.0, "strength": "none"}
    else:
        side = home if d > 0 else away
        out["lean"] = {"side": side, "side_spread": hs if d > 0 else -hs, "status": "lean",
                       "difference": abs(d), "strength": strength(abs(d))}
    return out


def select_original(versions: list[tuple[str, dict]], kickoff: datetime) -> tuple[str, dict] | None:
    """The version whose spread pick is locked: the earliest VALID version generated strictly before kickoff that has a
    market spread. versions: [(generated_at_iso, entry)]."""
    ok = [(t, e) for t, e in versions if datetime.fromisoformat(t) < kickoff and entry_is_valid(e)
          and (e.get("market") or {}).get("home_spread") is not None]
    return min(ok, key=lambda x: datetime.fromisoformat(x[0])) if ok else None


def lock_rule(kickoff: datetime) -> str:
    return "original-pick" if kickoff >= RULE_START else "final-pregame"


def select_locked(versions: list[tuple[str, dict]], kickoff: datetime) -> tuple[str, dict] | None:
    """The version whose spread pick is shown and graded under the rule in force for this game."""
    return select_original(versions, kickoff) if lock_rule(kickoff) == "original-pick" else select_frozen(versions, kickoff)


def grade(pick: dict | None, home_score: int, away_score: int, home: str, away: str) -> dict | None:
    """Grade a pick against the final score, using the line stored in the pick itself."""
    if not pick:
        return None
    a = home_score - away_score
    if a == 0:
        w = "tie"
    elif pick["winner"] is None:
        w = "no_pick"
    else:
        w = "win" if (pick["winner"] == home) == (a > 0) else "loss"
    lean = pick.get("lean") or {"status": "no_line"}
    if lean["status"] != "lean":
        s = lean["status"]                       # no_lean | no_line
    else:
        c = a - (-pick["line_home_spread"])      # actual margin vs line margin (home perspective)
        s = "push" if c == 0 else "win" if (c > 0) == (lean["side"] == home) else "loss"
    return {"winner": w, "lean": s, "abs_margin_error": abs(pick["projected_margin"] - a), "actual_margin": a}


def grade_game(final_pick: dict | None, locked_pick: dict | None, home_score: int, away_score: int, home: str,
               away: str) -> dict | None:
    """Winner and margin error from the final-pregame pick; the model pick (spread) from the locked pick against its
    own line ("no_line" when there is no locked pick)."""
    g = grade(final_pick, home_score, away_score, home, away)
    if g is None:
        return None
    o = grade(locked_pick, home_score, away_score, home, away)
    return {**g, "lean": o["lean"] if o else "no_line"}


GROUPS = ("publicly_verifiable_pregame", "generated_pregame_published_after_kickoff", "generated_pregame_not_yet_evidenced_public")


def _empty() -> dict:
    return {"graded": 0, "pick_graded": 0, "winner": {"win": 0, "loss": 0, "tie": 0, "no_pick": 0},
            "lean": {"win": 0, "loss": 0, "push": 0, "no_lean": 0, "no_line": 0},
            "abs_margin_error_sum": 0.0, "mean_abs_margin_error": None, "retro_winner": 0, "retro_pick": 0}


BIG_GAP = 3.0            # points between the stats-only margin and the line that the site tags "Big gap"


def grade_stats_only(locked_pick: dict | None, home_score: int, away_score: int) -> dict | None:
    """Display-only tracking record (user request 2026-10-09; not the official model pick): the side of the locked
    version's spread and total on which that same version's stats-only (football-only) numbers fell, graded against that
    line and total. A difference that rounds to 0.00 is no pick (None)."""
    so = (locked_pick or {}).get("stats_only")
    line = (locked_pick or {}).get("line_home_spread")
    if not so or line is None:
        return None
    a, t = home_score - away_score, home_score + away_score
    d = so["margin"] + line                  # > 0: the stats rate the home team above the line
    c = a + line                             # > 0: the home team covered
    spread = None if abs(d) < NO_LEAN else "push" if c == 0 else "win" if (c > 0) == (d > 0) else "loss"
    lt = so.get("line_total")
    dt = None if lt is None else so["total"] - lt
    total = (None if dt is None or abs(dt) < NO_LEAN else "push" if t == lt
             else "win" if (t > lt) == (dt > 0) else "loss")
    return {"spread": spread, "big_gap": abs(d) >= BIG_GAP, "total": total,
            "total_side": None if total is None else ("over" if dt > 0 else "under")}


def weekly_summary(items: list[dict]) -> dict:
    """items: exported game items with `status`, `forecast_verification`, `pick`, `locked_pick`, `result_grade`.
    The winner record and margin error are grouped by the final-pregame version's verification label (`graded`,
    `retro_winner`); the model pick record by the LOCKED version's label (`pick_graded`, `retro_pick`)."""
    groups = {g: _empty() for g in GROUPS}
    pending = no_forecast = 0
    for it in items:
        if it["status"] != "final":
            pending += 1
            continue
        gr = it.get("result_grade")
        if not gr:
            no_forecast += 1
            continue
        lk = it.get("locked_pick")
        s = groups.setdefault(it.get("forecast_verification") or "unlabelled", _empty())
        sp = groups.setdefault((lk or {}).get("verification") or it.get("forecast_verification") or "unlabelled", _empty())
        s["graded"] += 1
        s["winner"][gr["winner"]] += 1
        s["abs_margin_error_sum"] += gr["abs_margin_error"]
        s["retro_winner"] += int(bool(it["pick"].get("retrospectively_derived")))
        sp["pick_graded"] += 1
        sp["lean"][gr["lean"]] += 1
        sp["retro_pick"] += int(bool((lk or {}).get("retrospectively_derived")))
    for s in groups.values():
        if s["graded"]:
            s["mean_abs_margin_error"] = s["abs_margin_error_sum"] / s["graded"]
    rules = sorted({it["locked_pick"]["rule"] for it in items if it.get("locked_pick")})
    return {"state": "final" if pending == 0 else "week_to_date", "n_games": len(items), "pending": pending,
            "graded": sum(s["graded"] for s in groups.values()), "no_forecast": no_forecast, "groups": groups,
            "picks_version": PICKS_VERSION, "grading_rule": "+".join(rules) or None}
