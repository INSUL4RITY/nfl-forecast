"""Model picks and weekly results (display/reporting only; no model change).

A pick is derived from ONE forecast version and the market line archived IN THAT SAME version:
  * winner pick: the team with the higher win probability (exactly equal = toss-up, no pick);
  * projected winning margin: |projected margin|;
  * spread lean ("margin comparison"): d = projected margin - line margin, where line margin = -home_spread (the
    home team's expected margin implied by the line; project convention home_spread < 0 = home favoured).
    d > 0 leans to the home side of the line, d < 0 to the away side; |d| < NO_LEAN (displays as 0.00) = "No lean".
    The size of |d| is labelled so a tiny difference is never presented as a strong prediction.
Grading uses the version that scoring uses (final_pregame = latest valid version generated before kickoff), with that
version's own line, so later runs and line moves cannot change a graded pick. Actual ties, pushes, no-lean and no-line
cases are counted separately. Releases generated from picks-v1 on store the pick; for older versions the same rule is
applied now and the pick is flagged `retrospectively_derived`.
"""

from __future__ import annotations

PICKS_VERSION = "picks-v1"
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


GROUPS = ("publicly_verifiable_pregame", "generated_pregame_published_after_kickoff", "generated_pregame_not_yet_evidenced_public")


def _empty() -> dict:
    return {"graded": 0, "winner": {"win": 0, "loss": 0, "tie": 0, "no_pick": 0},
            "lean": {"win": 0, "loss": 0, "push": 0, "no_lean": 0, "no_line": 0},
            "abs_margin_error_sum": 0.0, "mean_abs_margin_error": None, "retrospectively_derived": 0}


def weekly_summary(items: list[dict]) -> dict:
    """items: exported game items with `status`, `forecast_verification`, `pick`, `result_grade`."""
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
        s = groups.setdefault(it.get("forecast_verification") or "unlabelled", _empty())
        s["graded"] += 1
        s["winner"][gr["winner"]] += 1
        s["lean"][gr["lean"]] += 1
        s["abs_margin_error_sum"] += gr["abs_margin_error"]
        s["retrospectively_derived"] += int(bool(it["pick"].get("retrospectively_derived")))
    for s in groups.values():
        if s["graded"]:
            s["mean_abs_margin_error"] = s["abs_margin_error_sum"] / s["graded"]
    return {"state": "final" if pending == 0 else "week_to_date", "n_games": len(items), "pending": pending,
            "graded": sum(s["graded"] for s in groups.values()), "no_forecast": no_forecast, "groups": groups,
            "picks_version": PICKS_VERSION}
