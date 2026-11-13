"""Team analytics: fixes from the November 2026 audit (one block per item)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "team_analytics"))
import build_html as bh  # noqa: E402
import reliability as rel  # noqa: E402


# ---- item 1: player tables rank on usage only; efficiency carries a reliability badge
def test_reliability_levels():
    assert rel.level(0.6) == "High" and rel.level(0.5) == "High"
    assert rel.level(0.3) == "Medium" and rel.level(0.2) == "Medium"
    assert rel.level(0.05) == "Low" and rel.level(None) is None and rel.level(float("nan")) is None


def test_player_efficiency_is_low_on_small_samples():
    assert rel.player_kept("carry", 10) < 0.05 and rel.level(rel.player_kept("carry", 10)) == "Low"
    assert rel.player_kept("carry", 10) < rel.player_kept("carry", 80) < rel.player_kept("carry", 250)
    assert rel.player_kept("target_TE", 80) == rel.player_kept("target_WR", 80)     # thin TE fit replaced by the WR fit
    assert rel.player_kept("carry", 0) is None


def test_player_tables_rank_usage_only():
    eff = bh.player_col_rule({"k": "epa_car", "l": "EPA/carry", "f": "epa", "d": 1, "t": ""})
    assert eff["d"] == 0 and eff["b"] == "rel_car"
    tgt = bh.player_col_rule({"k": "yac_pr", "l": "YAC/rec.", "f": "n1", "d": 1, "t": ""})
    assert tgt["d"] == 0 and tgt["b"] == "rel_tgt"
    prod = bh.player_col_rule({"k": "rush_yds", "l": "Rush yds", "f": "int", "d": 1, "t": ""})
    assert prod["d"] == 0 and "b" not in prod
    use = bh.player_col_rule({"k": "car_share", "l": "Carry share", "f": "pct", "d": 1, "t": ""})
    assert use["d"] == 1 and "b" not in use


# ---- item 2: special teams enter the combined rating shrunk, not at full weight
def test_special_teams_weight():
    import compute as cp
    fit = {"tau2": 1.0, "s2": 20.0}
    w = cp.st_weight([4, 9, 16], fit)
    assert 0 < w[0] < w[1] < w[2] < 1
    assert abs(w[1] - 1.0 / (1.0 + 20.0 / 9)) < 1e-12
    real = cp.st_weight([9])[0]                      # the fitted file: about a quarter kept after 9 games
    assert 0.15 < real < 0.4
    assert (cp.st_weight([9], {}) == 1.0).all()      # no fit: full weight, as before


# ---- item 3: headline edges report their record by measure; explosive runs are not a headline
def test_edge_record_by_measure_and_week():
    import numpy as np
    import pandas as pd
    import backtest_matchups as bm
    E = pd.DataFrame({"metric": ["epa_db"] * 4 + ["expl_run"] * 4, "W": [5, 9, 13, 14] * 2,
                      "z": [2.0, 2.0, -2.0, 0.1] * 2, "actual": [1.0, -1.0, -1.0, 1.0] * 2})
    z = E.z.abs()
    r = bm.edge_record(E, z, 1.0, 0.5)
    assert r["notable_cases"] == 3 and abs(r["notable_right"] - 2 / 3) < 1e-9          # headline measures only
    assert r["notable_by_measure"]["expl_run"]["cases"] == 3                           # still measured
    assert r["notable_by_weeks"]["4-7"] == {"cases": 1, "right": 1.0}
    assert "expl_run" not in r["headline_measures"]


def test_explosive_runs_are_not_a_headline_edge():
    assert "expl_run" not in [k for k, *_ in bh.EDGE_SPECS]
    cal = {"fitted_on": [2021, 2025], "edges": {"notable": 1.0, "notable_cases": 888, "notable_right": 0.673, "small": 0.5, "small_right": 0.533,
           "notable_by_measure": {"pressure": {"cases": 211, "right": 0.72}, "expl_run": {"cases": 106, "right": 0.575}},
           "notable_by_weeks": {"4-7": {"cases": 34, "right": 0.588}}}}
    t = bh.edge_note(cal)
    assert "pass rush vs protection 72% (211)" in t and "big runs are left out" in t and "weeks 4-7 had 34" in t


# ---- item 4: team-table cells get a reliability badge from the calibrated shrinkage weight
def test_team_badges_follow_the_shrinkage_weight():
    assert bh.REL_COLS["off_adj_epa"] == ("epa_play", "off") and bh.REL_COLS["def_adj_epa_rush"] == ("epa_rush", "def")
    assert bh.REL_COLS["off_epa_db"] == ("epa_db", "off") and bh.REL_COLS["def_rz_td_rate"] == ("rz_td", "def")
    MM = {"epa_play": {"off": {"w": {"AAA": 0.55}}, "def": {"w": {"AAA": 0.3}}}, "rz_td": {"off": {"w": {"AAA": 0.01}}, "def": {"w": {"AAA": 0.02}}}}
    b = bh.team_badges(MM, "AAA")
    assert b["rel__off_adj_epa"] == "High" and b["rel__off_epa_play"] == "High"
    assert b["rel__def_adj_epa"] == "Medium" and b["rel__off_rz_td_rate"] == "Low"
    assert "rel__off_epa_db" not in b                     # no model for that measure in this toy file: no badge


def test_player_badge_fields_reach_the_page():
    tables = [{"rows": "rb", "cols": [bh.player_col_rule({"k": "epa_car", "l": "EPA/carry", "f": "epa", "d": 1, "t": "", "n": "carries"})]}]
    US = {"rb": [{"name": "A", "team": "AAA", "epa_car": 0.1, "carries": 50, "rel_car": "Low", "secret": 1}], "wr": [], "te": [],
          "logs": {}, "team_players": {}}
    row = bh.trim_usage(US, tables)["rb"][0]
    assert row["rel_car"] == "Low" and "secret" not in row


# ---- item 5: raw tables flag teams whose schedule was more than 1 SD easier or harder
def test_schedule_flags():
    import pandas as pd
    T = pd.DataFrame({"sos_off": [0.05, -0.05, 0.0, 0.0, 0.0, 0.0], "sos_def": [0.0, 0.0, 0.05, -0.05, 0.0, 0.0]}, index=list("ABCDEF"))
    f = bh.sos_flags(T)
    assert f["A"] == {"sos_flag_off": "softer schedule"}       # faced defences that allow more
    assert f["B"] == {"sos_flag_off": "harder schedule"}
    assert f["C"] == {"sos_flag_def": "harder schedule"}       # faced stronger offences
    assert f["D"] == {"sos_flag_def": "softer schedule"}
    assert f["E"] == {} and f["F"] == {}
    assert "rank_rb" in bh.SOS_TABLES["off"] and "eff_def" in bh.SOS_TABLES["def"] and "sos" not in bh.SOS_TABLES["off"]


# ---- item 6: forward-only validation never fits on the season it predicts, or later ones
def test_forward_check_uses_only_earlier_seasons(monkeypatch):
    import numpy as np
    import pandas as pd
    import backtest_matchups as bm
    rng = np.random.default_rng(0)
    rows = [{"season": s, "metric": m, "W": w, "n": 50, "shr": x, "actual": 0.5 * x + rng.normal(0, 0.1)}
            for s in (2021, 2022, 2023) for m in ("a", "b") for w in (5, 10) for x in rng.normal(0, 1, 20)]
    Z = pd.DataFrame(rows)
    seen = []
    real_fit = bm.fit

    def spy(z):
        seen.append(sorted(z.season.unique()))
        return real_fit(z)
    monkeypatch.setattr(bm, "fit", spy)
    out = bm.forward_check(Z)
    assert set(out) == {"a", "b"} and out["a"]["seasons"] == [2022, 2023]
    assert all(max(s) < t for s, t in zip(seen, [2022, 2023, 2022, 2023]))      # each fit is on earlier seasons only
    assert out["a"]["error_after"] < out["a"]["error_before"]                   # actual = half the expectation: calibration helps


# ---- item 7: game-level variance in the matchup shrinkage
def _games(game_sd, seed):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(400):
        shift = rng.normal(0, game_sd)
        for _ in range(60):
            rows.append({"game_id": f"g{g}", "posteam": f"T{g % 20}", "r": shift + rng.normal(0, 1.0)})
    d = pd.DataFrame(rows)
    return d, d.r, pd.Series(1.0, index=d.index)


def test_game_variance_recovers_shared_game_shifts():
    import compute as cp
    d, r, v = _games(0.3, 1)
    gv = cp.game_variance(r, d, "posteam", v)
    assert abs(gv - 0.09) < 0.03                           # true game variance 0.3^2
    d0, r0, v0 = _games(0.0, 2)
    assert cp.game_variance(r0, d0, "posteam", v0) < 0.01   # independent plays: no excess


def test_game_variance_lowers_the_weight():
    import numpy as np
    import pandas as pd
    import compute as cp
    rng = np.random.default_rng(3)
    teams = [f"T{i}" for i in range(8)]
    rows = []
    for w in range(1, 6):
        for i in range(0, 8, 2):
            o, dd = teams[i], teams[i + 1]
            for side_o, side_d in ((o, dd), (dd, o)):
                shift = rng.normal(0, 0.25) + (0.1 if side_o in ("T0", "T2") else 0)
                for _ in range(30):
                    rows.append({"game_id": f"{w}_{o}", "week": w, "posteam": side_o, "defteam": side_d, "is_home": 0,
                                 "location": "Home", "home_team": o, "y": shift + rng.normal(0, 1)})
    d = pd.DataFrame(rows)
    a = cp.adjust(d, "y", teams)
    assert len(a["resid"]) == len(d)
    gv = cp.game_variance(a["resid"], d, "posteam", pd.Series(a["resid_var"], index=d.index))
    assert gv > 0
    n, games = 150, 5
    assert a["resid_var"] / n + gv / games > a["resid_var"] / n      # more noise per team, so a smaller weight


def test_game_variance_is_off_in_the_report():
    import compute as cp
    assert cp.GAME_VAR is False      # tested on 2021-25 and not adopted (game_variance_test.json)


# ---- item 8: opponent-adjusted QB refit uses only earlier weeks' defence effects for the sample
def test_adjusted_dropbacks_use_only_earlier_weeks():
    import numpy as np
    import pandas as pd
    import backtest_qb_sample as bq
    rng = np.random.default_rng(4)
    teams = ["AAA", "BBB", "CCC", "DDD"]
    rows = []
    for w in range(1, 6):
        for i, (o, d) in enumerate((("AAA", "BBB"), ("CCC", "DDD"), ("BBB", "AAA"), ("DDD", "CCC"))):
            for k in range(25):
                rows.append({"game_id": f"{w}_{i // 2}", "play_id": k + 100 * i, "week": w, "posteam": o, "defteam": d, "is_home": 1 if i % 2 == 0 else -1,
                             "db": True, "passer_id": f"QB_{o}", "epa": rng.normal(0.3 if d == "DDD" else 0.0, 1.0)})
    p = pd.DataFrame(rows)
    a = bq.adjusted_dropbacks(p)
    w1 = a[a.week == 1]
    assert np.allclose(w1.epa_prior, w1.epa)                       # no earlier weeks: nothing subtracted
    later = p.copy()
    later.loc[(later.week == 5) & (later.defteam == "DDD"), "epa"] += 5.0   # change only week 5, against one defence
    b = bq.adjusted_dropbacks(later)
    k = ["game_id", "play_id"]
    m = a[a.week == 4].set_index(k).epa_prior.sort_index(), b[b.week == 4].set_index(k).epa_prior.sort_index()
    assert np.allclose(m[0], m[1])                                 # week 4's sample adjustment does not see week 5
    assert not np.allclose(a[a.week == 4].set_index(k).epa_full.sort_index(), b[b.week == 4].set_index(k).epa_full.sort_index())


def test_qb_refit_result_is_recorded_and_not_adopted():
    import json
    from pathlib import Path
    q = json.loads((Path(bh.__file__).resolve().parent / "qb_shrinkage.json").read_text(encoding="utf-8"))
    oa = q["opponent_adjusted"]
    assert oa["use_adjusted"] is False and oa["adjusted"]["loso_rmse"] > oa["raw"]["loso_rmse"]
    assert oa["adjusted"]["backup_gap"] < -0.05 and oa["raw"]["backup_gap"] < -0.05     # the backup offset holds either way
