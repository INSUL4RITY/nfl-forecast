"""Team analytics: hand-kept quarterback news (trades, named starters) applied to the QB scenarios."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import build_html as bh  # noqa: E402
import context as ctx  # noqa: E402


def qrow(pid, name, starts, db, latest, adj=0.0):
    return {"id": pid, "name": name, "dropbacks": db, "starts": starts, "start_weeks": list(range(1, starts + 1)),
            "adj_epa_db": adj, "epa_db": adj, "sr": 0.45, "sack_rate": 0.06, "int_worthy": 0.03, "roster_status": "ACT",
            "report_status": None, "practice_status": None, "report_week": None, "latest_starter": latest}


def pbp():
    """Two dropbacks per game: AAA starts with Old Qb (weeks 1-2), BBB starts with Moved Qb (weeks 1-2)."""
    rows = []
    for w in (1, 2, 3):
        for team, pid in (("AAA", "A1"), ("BBB", "B1")):
            for k in range(3):
                rows.append({"game_id": f"2026_0{w}_{team}_X", "play_id": k, "week": w, "posteam": team, "db": True, "passer_id": pid})
    return pd.DataFrame(rows)


Q = pd.DataFrame([
    {"passer_id": "A1", "name": "O.Qb", "name_full": "Old Qb", "teams": "AAA", "dropbacks": 300, "epa_db": 0.1, "adj_epa_db": 0.12, "sr": 0.5,
     "sack_rate": 0.05, "int_worthy_rate": 0.02, "epa_vs_blitz": 0.0, "db_blitz": 80, "db_hit": 60, "epa_hit_sack": -1.0, "scr_rate": 0.03},
    {"passer_id": "B1", "name": "M.Qb", "name_full": "Moved Qb Jr.", "teams": "BBB", "dropbacks": 250, "epa_db": -0.02, "adj_epa_db": -0.01, "sr": 0.44,
     "sack_rate": 0.07, "int_worthy_rate": 0.03, "epa_vs_blitz": -0.1, "db_blitz": 60, "db_hit": 50, "epa_hit_sack": -1.2, "scr_rate": 0.05},
])


def scen():
    return {"AAA": {"qbs": [qrow("A1", "Old Qb", 3, 300, True, 0.12)], "latest": "A1", "primary": "A1", "flags": []},
            "CCC": {"qbs": [qrow("C1", "Third Qb", 3, 200, True)], "latest": "C1", "primary": "C1", "flags": []}}


NEWS = {"AAA": {"starter": "Rookie Qb", "conf": "named", "sources": [{"who": "Reporter", "what": "named", "when": "2026-11-10"}],
                "unavailable": [{"player": "Old Qb", "why": "traded to CCC"}]},
        "CCC": {"starter": "Moved Qb", "conf": "expected", "sources": [{"who": "Reporter", "what": "expected", "when": "2026-11-10"}]}}


def test_rookie_without_a_sample_becomes_the_expected_starter():
    s = scen()
    lines = ctx.apply_qb_news(s, NEWS, Q, pbp(), 4)
    assert lines == ["AAA Rookie Qb (named)", "CCC Moved Qb (expected)"]
    q = bh.expected_starter(s["AAA"])
    assert q["name"] == "Rookie Qb" and q["dropbacks"] == 0 and q["adj_epa_db"] is None
    line = bh.starter_line("AAA", s["AAA"])
    assert line["news"] == "named" and line["no_sample"] and "Reporter, 2026-11-10" in line["sources"]
    old = next(r for r in s["AAA"]["qbs"] if r["name"] == "Old Qb")
    assert old["news_status"] == "traded to CCC"
    assert "no 2026 regular-season dropbacks" in s["AAA"]["flags"][-1] and "Old Qb (3 starts) traded to CCC" in s["AAA"]["flags"][-1]


def test_traded_starter_brings_his_sample_from_the_old_team():
    s = scen()
    ctx.apply_qb_news(s, NEWS, Q, pbp(), 4)
    line = bh.starter_line("CCC", s["CCC"])
    assert line["name"] == "Moved Qb" and line["starts"] == 3 and line["dropbacks"] == 250
    assert line["sample_team"] == "BBB" and line["adj_epa_db"] == -0.01 and line["news"] == "expected"
    assert "with BBB" in s["CCC"]["flags"][-1]


def test_qb_context_leads_with_the_reported_starter():
    s = scen()
    ctx.apply_qb_news(s, NEWS, Q, pbp(), 4)
    m = {"epa_db": {"mean": 0.0, "resid_var": 1.8, "home": 0.0, "off": {"tau2": 0.01}, "def": {"w": {"DDD": 0.5}, "eff": {"DDD": 0.0}}}}
    cx = bh.qb_context("CCC", "DDD", m, s, None, 0)
    assert cx["text"].startswith("expected EPA/dropback vs DDD with Moved Qb (expected starter, not confirmed)")
    assert "with Third Qb" in cx["text"] and cx["caution"]
    ax = bh.qb_context("AAA", "DDD", m, s, None, 0)
    assert ax["text"].startswith("no 2026 sample for Rookie Qb")


def test_no_news_leaves_the_rule_unchanged():
    s = scen()
    assert ctx.apply_qb_news(s, {}, Q, pbp(), 4) == []
    assert bh.expected_starter(s["AAA"])["name"] == "Old Qb" and bh.starter_line("AAA", s["AAA"]) is None
    assert "no hand-kept entries" in ctx.qb_news_qc([], 4)
