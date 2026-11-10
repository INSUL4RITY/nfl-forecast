import polars as pl
import pytest

from nflcast.predict import deserved as DS


def _plays(rows):
    cols = {c: [] for c in DS.PBP_COLS}
    for r in rows:
        base = {"game_id": "g", "posteam": None, "defteam": None, "play_type": "pass", "epa": 0.0, "yards_gained": 0.0,
                "interception": 0, "fumble_lost": 0, "return_yards": 0.0, "fumble_recovery_1_yards": 0.0, "two_point_attempt": 0}
        base.update(r)
        for c in DS.PBP_COLS:
            cols[c].append(base[c])
    return pl.DataFrame(cols, strict=False)


def test_takeaways_fold_into_the_takers_rate_and_yards():
    pbp = _plays([
        {"posteam": "H", "defteam": "A", "epa": 0.5, "yards_gained": 10},
        {"posteam": "H", "defteam": "A", "epa": -0.2, "yards_gained": 2},
        {"posteam": "A", "defteam": "H", "epa": -3.0, "interception": 1, "return_yards": 20},
        {"posteam": "A", "defteam": "H", "epa": -2.0, "play_type": "run", "fumble_lost": 1, "yards_gained": 4,
         "fumble_recovery_1_yards": 6},
        {"posteam": "A", "defteam": "H", "epa": 1.0, "yards_gained": 30},
        {"posteam": "A", "defteam": "H", "epa": 5.0, "two_point_attempt": 1},     # excluded
        {"posteam": "A", "defteam": "H", "epa": 2.0, "play_type": "punt"},        # excluded
    ])
    q = DS.team_quality(pbp)
    h, a = q[("g", "H")], q[("g", "A")]
    assert h["plays"] == 2 and h["takeaways"] == 2
    assert h["success_rate"] == pytest.approx((1 + 2) / (2 + 2))
    assert h["yards_per_play"] == pytest.approx((12 + 20 + 6) / 2)
    assert a["plays"] == 3 and a["takeaways"] == 0
    assert a["success_rate"] == pytest.approx(1 / 3) and a["yards_per_play"] == pytest.approx(34 / 3)


def test_groups_and_sides():
    w = DS.config()["weights"]
    q = {("g", "H"): {"plays": 60, "takeaways": 0, "success_rate": 0.5, "yards_per_play": 6.0},
         ("g", "A"): {"plays": 60, "takeaways": 0, "success_rate": 0.4, "yards_per_play": 5.0}}
    dm = w["success_rate"] * 0.1 + w["yards_per_play"] * 1.0          # ~9.6 to the home team
    lp = lambda side, line, ver="publicly_verifiable_pregame": {"lean": {"side": side}, "line_home_spread": line, "verification": ver}
    d = DS.game_deserved(q, "g", "H", "A", lp("H", -3.0), {"lean": "loss"})
    assert d["margin"] == pytest.approx(dm) and d["pick"]["quality"] == "ahead" and d["pick"]["group"] == "wrong_unlucky"
    d = DS.game_deserved(q, "g", "H", "A", lp("A", -3.0), {"lean": "win"})
    assert d["pick"]["group"] == "right_fortunate" and d["pick"]["edge"] == pytest.approx(-(dm - 3.0))
    assert DS.game_deserved(q, "g", "H", "A", lp("A", -9.0), {"lean": "win"})["pick"]["group"] == "close"
    assert DS.game_deserved(q, "g", "H", "A", lp("H", -3.0), {"lean": "push"})["pick"]["group"] == "level"
    assert DS.game_deserved(q, "g", "H", "A", lp("H", -3.0), {"lean": "win"})["pick"]["group"] == "right_deserved"
    assert DS.game_deserved(q, "g", "H", "A", lp("A", -3.0), {"lean": "loss"})["pick"]["group"] == "wrong_deserved"
    assert DS.game_deserved(q, "g", "H", "A", None, None)["pick"] is None             # no pick: margin only
    assert DS.game_deserved(q, "x", "H", "A", lp("H", -3.0), {"lean": "win"}) is None  # no play-by-play


def test_summary_counts_publicly_verifiable_only():
    q = {("g", "H"): {"plays": 60, "takeaways": 0, "success_rate": 0.5, "yards_per_play": 6.0},
         ("g", "A"): {"plays": 60, "takeaways": 0, "success_rate": 0.4, "yards_per_play": 5.0}}
    mk = lambda ver: {"game_id": "g", "week": 10, "home": "H", "away": "A", "score": {"home": 20, "away": 17},
                      "deserved": DS.game_deserved(q, "g", "H", "A", {"lean": {"side": "H"}, "line_home_spread": -3.0,
                                                                     "verification": ver}, {"lean": "push"})}
    s = DS.summary([mk("publicly_verifiable_pregame"), mk("generated_pregame_published_late"), {"deserved": None}])
    assert s["n"] == 1 and s["counts"]["level"] == 1 and s["games"][0]["actual_margin"] == 3


def test_config_weights_are_the_fixed_ones():
    c = DS.config()
    assert c["weights"] == {"success_rate": 55.429, "yards_per_play": 4.050} and c["close_band"] == 1.5


def _game(n_good_home=30, n_home=60, n_good_away=20, n_away=60):
    rows = []
    for i in range(n_home):
        rows.append({"posteam": "H", "defteam": "A", "epa": 0.5 if i < n_good_home else -0.4, "yards_gained": 8 if i < n_good_home else 1})
    for i in range(n_away):
        rows.append({"posteam": "A", "defteam": "H", "epa": 0.5 if i < n_good_away else -0.4, "yards_gained": 8 if i < n_good_away else 1})
    return _plays(rows)


def test_chance_is_reproducible_and_tracks_the_edge():
    q = DS.team_quality(_game())
    lp = lambda side, line: {"lean": {"side": side}, "line_home_spread": line, "verification": "publicly_verifiable_pregame"}
    d1 = DS.game_deserved(q, "g", "H", "A", lp("H", -3.0), {"lean": "win"})
    d2 = DS.game_deserved(q, "g", "H", "A", lp("H", -3.0), {"lean": "win"})
    c = d1["pick"]["chance"]
    assert c == d2["pick"]["chance"] and 0.5 < c <= 1.0                      # same seed per game; home clearly better
    other = DS.game_deserved(q, "g", "H", "A", lp("A", -3.0), {"lean": "loss"})["pick"]["chance"]
    assert other == pytest.approx(1 - c, abs=1e-9)                           # the two sides of the same line
    far = DS.game_deserved(q, "g", "H", "A", lp("H", -60.0), {"lean": "loss"})["pick"]["chance"]
    assert far < 0.01
    assert "_draw" not in d1["home"]                                         # internal arrays are never exported


def test_resampled_margins_centre_on_the_point_estimate():
    q = DS.team_quality(_game())
    m = DS.resampled_margins("g", q[("g", "H")]["_draw"], q[("g", "A")]["_draw"])
    assert abs(m.mean() - DS.deserved_margin(q[("g", "H")], q[("g", "A")])) < 0.5 and m.std() > 0


def test_ledger_counts():
    base = {"game_id": "g", "play_type": "pass", "epa": 0.0, "yards_gained": 0.0, "interception": 0, "fumble_lost": 0,
            "return_yards": 0.0, "fumble_recovery_1_yards": 0.0, "two_point_attempt": 0, "special_teams_play": 0,
            "field_goal_attempt": 0, "field_goal_result": None, "penalty": 0, "penalty_team": None, "penalty_yards": None,
            "fixed_drive": 1.0, "fixed_drive_result": "Touchdown", "drive_inside20": 1.0, "yardline_100": 75.0,
            "fourth_down_converted": 0, "fourth_down_failed": 0}
    rows = [
        {"posteam": "H", "defteam": "A", "yards_gained": 25.0, "yardline_100": 75.0},                       # explosive pass
        {"posteam": "H", "defteam": "A", "play_type": "run", "yards_gained": 12.0, "yardline_100": 50.0,
         "fourth_down_converted": 1},
        {"posteam": "H", "defteam": "A", "interception": 1, "yardline_100": 15.0, "penalty": 1, "penalty_team": "A",
         "penalty_yards": 5.0},
        {"posteam": "A", "defteam": "H", "fixed_drive": 2.0, "fixed_drive_result": "Missed field goal", "drive_inside20": 0.0,
         "yardline_100": 70.0, "play_type": "run", "yards_gained": 3.0, "fumble_lost": 1},
        {"posteam": "A", "defteam": "H", "fixed_drive": 2.0, "fixed_drive_result": "Missed field goal", "drive_inside20": 0.0,
         "play_type": "field_goal", "special_teams_play": 1, "field_goal_attempt": 1, "field_goal_result": "missed",
         "epa": -2.0, "yardline_100": 35.0},
        {"posteam": None, "defteam": None, "play_type": "no_play", "penalty": 1, "penalty_team": "A", "penalty_yards": 15.0,
         "fixed_drive": None},
    ]
    df = pl.DataFrame([{**base, **r} for r in rows], strict=False).select(DS.LEDGER_COLS)
    led = DS.team_ledger(df)
    h, a = led[("g", "H")], led[("g", "A")]
    assert (h["interceptions"], h["explosive"], h["fourth_conv"], h["fourth_att"], h["rz_td"], h["rz_trips"]) == (1, 2, 1, 1, 1, 1)
    assert h["avg_start"] == pytest.approx(25.0) and a["avg_start"] == pytest.approx(30.0)
    assert (a["fumbles_lost"], a["fg_made"], a["fg_att"], a["rz_trips"]) == (1, 0, 1, 0)
    assert (a["penalties"], a["penalty_yards"]) == (2, 20)                   # includes a penalty with no possession team
    assert h["st_epa"] == pytest.approx(2.0) and a["st_epa"] == pytest.approx(-2.0)
