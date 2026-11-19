"""Team analytics: blitz outcomes, hot/cold verdicts and the depleted-line flag (added for the week 11 build)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import compute as cp  # noqa: E402


# ---- blitz outcomes
def test_blitz_outcomes_add_up_and_classify():
    rows = [  # defteam D blitzes on all four: sack, completion of 25, incompletion, scramble of 6; one non-blitz interception
        {"defteam": "D", "posteam": "O", "blitz": True, "sack": 1, "qb_scramble": 0, "interception": 0, "complete_pass": 0, "success": 0, "yards_gained": -7, "epa": -2.0},
        {"defteam": "D", "posteam": "O", "blitz": True, "sack": 0, "qb_scramble": 0, "interception": 0, "complete_pass": 1, "success": 1, "yards_gained": 25, "epa": 1.8},
        {"defteam": "D", "posteam": "O", "blitz": True, "sack": 0, "qb_scramble": 0, "interception": 0, "complete_pass": 0, "success": 0, "yards_gained": 0, "epa": -0.5},
        {"defteam": "D", "posteam": "O", "blitz": True, "sack": 0, "qb_scramble": 1, "interception": 0, "complete_pass": 0, "success": 1, "yards_gained": 6, "epa": 0.3},
        {"defteam": "D", "posteam": "O", "blitz": False, "sack": 0, "qb_scramble": 0, "interception": 1, "complete_pass": 0, "success": 0, "yards_gained": 0, "epa": -3.0},
    ]
    T = pd.DataFrame(index=["D", "O"])
    cp.blitz_outcomes(pd.DataFrame(rows), T)
    r = T.loc["D"]
    assert r.def_out_sack_blitz == 0.25 and r.def_out_cmp_blitz == 0.25 and r.def_out_inc_blitz == 0.25 and r.def_out_scr_blitz == 0.25
    assert sum(r[f"def_out_{o}_blitz"] for o in cp.BLITZ_OUTCOMES) == 1.0
    assert r.def_out_expl_blitz == 0.25 and r.def_out_succ_blitz == 0.5
    assert r.def_out_int_noblitz == 1.0
    assert abs(r.def_blitz_epa_gain - ((-2.0 + 1.8 - 0.5 + 0.3) / 4 - (-3.0))) < 1e-12
    assert T.loc["O"].off_out_sack_blitz == 0.25                          # the offence's view of the same plays


# ---- hot and cold teams
def _hc_frames():
    import build_html as bh  # noqa: F401
    teams = ["LUK", "GOOD", "UNL", "BAD", "MID"]
    T = pd.DataFrame({"stab_rating_pg": [-3.0, 8.0, 1.0, -9.0, 0.5], "luck_index": [1.6, 0.2, -1.2, 0.1, 0.0],
                      "one_w": [5, 3, 1, 1, 2], "one_l": [0, 1, 5, 3, 2], "to_luck": [2.0, 0.0, -1.0, -3.0, 0.0],
                      "form_net_change": [0.01, 0.05, 0.1, -0.1, 0.0], "record": ["7-2", "6-3", "3-6", "1-8", "4-5"]}, index=teams)
    T = pd.concat([T, pd.DataFrame({"stab_rating_pg": np.linspace(-6, 6, 27), "luck_index": 0.0, "one_w": 2, "one_l": 2, "to_luck": 0.0,
                                    "form_net_change": 0.0, "record": "4-4"}, index=[f"X{i}" for i in range(27)])])
    wins = {"LUK": [1, 1, 1, 1], "GOOD": [1, 0, 1, 1], "UNL": [0, 0, 1, 0], "BAD": [0, 0, 0, 0], "MID": [1, 0, 1, 0]}
    G = pd.DataFrame([{"team": t, "week": w + 1, "win": x} for t, ws in wins.items() for w, x in enumerate(ws)])
    return T, G


def test_hot_cold_verdicts():
    import build_html as bh
    T, G = _hc_frames()
    hc = bh.hot_cold(T, G)
    assert set(hc) == {"LUK", "GOOD", "UNL", "BAD"}                      # MID went 2-2 with no luck: not listed
    assert hc["LUK"]["trend"] == "Hot" and hc["LUK"]["verdict"].startswith("Lucky streak")
    assert hc["GOOD"]["verdict"] == "Real: a good team winning" and hc["GOOD"]["last4"] == "WLWW"
    assert hc["UNL"]["trend"] == "Cold" and hc["UNL"]["verdict"].startswith("Unlucky")
    assert hc["BAD"]["verdict"] == "Genuinely bad"


def test_no_streak_but_lucky_is_listed():
    import build_html as bh
    T, G = _hc_frames()
    T.loc["MID", "luck_index"] = -1.3                                  # 2-2 in its last four, but well behind its play
    hc = bh.hot_cold(T, G)
    assert hc["MID"]["trend"] == "No streak" and hc["MID"]["verdict"].startswith("Unlucky")


# ---- offensive line starters out
def test_line_starters_out_and_caution():
    import build_html as bh
    A = pd.DataFrame([
        {"team": "OFF", "player": "Left Tackle", "group": "OL", "status_class": "listed Out/Doubtful", "share": 0.98, "term": "new", "out_since_week": 10},
        {"team": "OFF", "player": "Swing Guard", "group": "OL", "status_class": "listed Out/Doubtful", "share": 0.30, "term": "new", "out_since_week": 10},
        {"team": "OFF", "player": "Centre", "group": "OL", "status_class": "listed Questionable", "share": 0.95, "term": "new", "out_since_week": 10},
        {"team": "OFF", "player": "Right Guard", "group": "OL", "status_class": "confirmed: reserve list", "share": 0.90, "term": "long-term", "out_since_week": 6},
        {"team": "OFF", "player": "Receiver", "group": "WR/TE", "status_class": "listed Out/Doubtful", "share": 0.90, "term": "new", "out_since_week": 10},
    ])
    out = bh.line_starters_out(A, "OFF")
    assert list(out.player) == ["Left Tackle", "Right Guard"]                 # starters confirmed out only
    T = pd.DataFrame({"def_pressure_rate": np.linspace(0.15, 0.30, 4)}, index=["OFF", "DEF", "X", "Y"])
    c = bh.line_caution("OFF", "DEF", A, T)
    assert c.startswith("OFF offensive line: 2 starters out") and "out since week 6" in c and "partly in the season figures" in c
    assert bh.line_caution("DEF", "OFF", A, T) is None
    if bh.LINE_BT:
        assert "not larger against strong pass rushes" in c


# ---- quarterback rows: a short-sample latest starter is kept, a traded quarterback is not expected
def test_qb_scenarios_latest_starter_and_departed():
    import context as ctx
    import build_html as bh
    rows, pid = [], 0
    # weeks 1-8 started by OLD (40 dropbacks each); week 9 NEW starts with 12 dropbacks; week 10 STAR starts, gets hurt, RELIEF throws more
    plan = {w: [("OLD", 40)] for w in range(1, 9)}
    plan[9] = [("NEW", 12)]
    plan[10] = [("NEW", 8), ("RELIEF", 9)]
    for w, seq in plan.items():
        for qb, n in seq:
            for _ in range(n):
                pid += 1
                rows.append({"game_id": f"2026_{w:02d}_ARI_XXX", "play_id": pid, "week": w, "posteam": "ARI", "passer_id": qb, "db": True,
                             "sc": True, "epa": 0.0, "qtr": 1})
    p = pd.DataFrame(rows)
    Q = pd.DataFrame({"passer_id": ["OLD", "NEW", "RELIEF"], "name_full": ["Old Starter", "New Starter", "Relief Arm"], "name": ["O", "N", "R"]})
    for c in ("epa_db", "adj_epa_db", "sr", "sack_rate", "int_worthy_rate", "epa_vs_blitz", "epa_hit_sack", "scr_rate"):
        Q[c] = 0.0
    Q["db_blitz"], Q["db_hit"] = 0, 0
    ros = pd.DataFrame({"gsis_id": ["OLD", "NEW", "RELIEF"], "status": ["ACT"] * 3, "team": ["BAL", "ARI", "ARI"]})
    inj = pd.DataFrame(columns=["gsis_id", "report_status", "practice_status", "week"])
    out = ctx.qb_scenarios(p, Q, ros, inj, ["ARI"], 10)["ARI"]
    names = {r["name"]: r for r in out["qbs"]}
    assert "New Starter" in names and names["New Starter"]["latest_starter"]       # 20 dropbacks, but he started the latest game
    assert not names.get("Relief Arm", {}).get("latest_starter", False)              # more dropbacks in week 10, but did not start it
    assert names["Old Starter"]["now_team"] == "BAL"
    assert any("is now on BAL's roster" in f for f in out["flags"])
    assert bh.expected_starter(out)["name"] == "New Starter"
