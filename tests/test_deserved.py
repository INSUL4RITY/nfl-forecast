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
