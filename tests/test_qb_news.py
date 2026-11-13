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
    assert ax["text"].startswith("expected EPA/dropback vs DDD with Rookie Qb (reported starter; did not open the season as a starter; no 2026 sample)")
    assert abs(ax["rows"][-1]["exp_db"] - bh.ROLE["backup_adj"]) < 1e-9 or any(abs(r["exp_db"] - bh.ROLE["backup_adj"]) < 1e-9 for r in ax["rows"])


def test_no_news_leaves_the_rule_unchanged():
    s = scen()
    assert ctx.apply_qb_news(s, {}, Q, pbp(), 4) == []
    assert bh.expected_starter(s["AAA"])["name"] == "Old Qb" and bh.starter_line("AAA", s["AAA"]) is None
    assert "no hand-kept entries" in ctx.qb_news_qc([], 4)


def test_one_quarter_flags_a_total_carried_by_one_quarter():
    rows = [{"week": 1, "qtr": 4, "epa": 1.0}] * 8 + [{"week": 1, "qtr": 2, "epa": -0.05}] * 20 + [{"week": 2, "qtr": 1, "epa": 0.05}] * 20
    o = ctx.one_quarter(pd.DataFrame(rows))
    assert o["week"] == 1 and o["qtr"] == 4 and o["epa"] == 8.0 and o["n"] == 8 and o["without"] == 0.0
    even = pd.DataFrame([{"week": w, "qtr": q, "epa": 0.1} for w in (1, 2) for q in (1, 2, 3, 4) for _ in range(5)])
    assert ctx.one_quarter(even) is None


def test_qb_weight_uses_the_fitted_quarterback_spread():
    assert bh.QB_SHRINK is not None
    w60, w200 = bh.qb_weight(60), bh.qb_weight(200)
    assert 0.1 < w60 < w200 < 0.5
    assert "uncertain by about" in bh.sample_note({"dropbacks": 51, "adj_epa_db": 0.18, "one_q": None})


def test_player_rates_show_a_range_and_point_to_usage():
    import nextup
    q = {"kind": "skill", "pos": "WR", "games": 4, "snap_pct": 0.6, "targets": 14, "epa_tgt": 0.31, "carries": 3, "epa_car": 0.1}
    t = nextup.text("Next Man", q)
    assert "+0.310 EPA/target, ±0.8" in t and "(too few for a rate)" in t and "steadier guide" in t
    assert "Efficiency settles slowly" in bh.player_note("rec") and "Efficiency settles slowly" in bh.player_note("rb")


def test_backup_role_lowers_the_expectation_and_is_flagged():
    m = {"epa_db": {"mean": 0.0, "resid_var": 1.8, "home": 0.0, "off": {"tau2": 0.01}, "def": {"w": {"DDD": 0.5}, "eff": {"DDD": 0.0}}}}
    hot_backup = dict(qrow("B9", "Hot Backup", 2, 51, True, 0.26), opened_season=False)
    starter = dict(qrow("S1", "Long Starter", 5, 198, False, -0.10), opened_season=True)
    e_b = bh.qb_expect(hot_backup, m["epa_db"], 0.5, 0.0, 0)
    e_s = bh.qb_expect(starter, m["epa_db"], 0.5, 0.0, 0)
    assert e_b < e_s                      # 51 hot dropbacks by a backup no longer beat 198 poor ones by the starter
    assert "did not open the season" in bh.role_text(hot_backup) and bh.role_text(starter) == ""


def test_ngs_signature_lists_only_extreme_tendencies():
    rec = {"def_zone": 0.84, "def_zone_pct": 87, "def_man": 0.16, "def_man_pct": 13, "def_blitz": 0.32, "def_blitz_pct": 50,
           "off_tempo_sec": 32.6, "off_tempo_sec_pct": 93}
    s = bh.ngs_signature(rec, "def_")
    assert "zone coverage 84% (high, 87th percentile)" in s and "man coverage 16% (low, 13th percentile)" in s and "blitz" not in s
    assert "seconds between snaps 32.6 s (fast, 93rd percentile)" == bh.ngs_signature(rec, "off_")
    assert bh.ngs_signature({"def_blitz": 0.3, "def_blitz_pct": 50}, "def_") == "no tendency in the top or bottom fifth"
