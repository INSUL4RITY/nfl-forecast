from datetime import datetime, timezone

import numpy as np
import polars as pl

from nflcast.data.games import build_games
from nflcast.models.core import MarketRaw, coherent


def _sched(**over):
    base = {"game_id": "2026_03_GB_ATL", "season": 2026, "game_type": "REG", "week": 3, "gameday": "2026-09-27",
            "weekday": "Sunday", "gametime": "13:00", "away_team": "GB", "home_team": "ATL", "away_score": None,
            "home_score": None, "location": "Home", "stadium_id": "ATL97", "stadium": "X", "roof": "dome",
            "surface": "fieldturf", "div_game": 0, "home_rest": 7, "away_rest": 7, "home_qb_id": None,
            "away_qb_id": None, "home_qb_name": None, "away_qb_name": None, "home_coach": None, "away_coach": None,
            "overtime": None, "spread_line": -5.5, "total_line": 42.5}
    base.update(over)
    return pl.DataFrame([base], schema_overrides={"away_score": pl.Int32, "home_score": pl.Int32, "overtime": pl.Int32,
                                                    "home_qb_id": pl.Utf8, "away_qb_id": pl.Utf8, "home_qb_name": pl.Utf8,
                                                    "away_qb_name": pl.Utf8, "home_coach": pl.Utf8, "away_coach": pl.Utf8})


def test_green_bay_minus_5_5_away_maps_to_home_margin_minus_5_5():
    # nflverse spread_line = expected HOME margin. Away GB favoured by 5.5 => spread_line = -5.5,
    # project home_spread s = +5.5 (home underdog), M0 = -s = -5.5.
    s = _sched()
    home_spread = -s["spread_line"]
    p = MarketRaw().predict(pl.DataFrame({"home_spread": home_spread, "total": s["total_line"]}))
    assert p["margin"][0] == -5.5
    assert np.isclose(p["home_pts"][0], 18.5) and np.isclose(p["away_pts"][0], 24.0)


def test_green_bay_minus_5_5_at_home_is_plus_5_5_home_margin():
    # Brief: "Green Bay -5.5 when Green Bay is home corresponds to a +5.5 home-margin benchmark."
    p = MarketRaw().predict(pl.DataFrame({"home_spread": [-5.5], "total": [42.5]}))
    assert p["margin"][0] == 5.5


def test_coherence_full_precision():
    rng = np.random.default_rng(1)
    M, T = rng.normal(0, 7, 1000), rng.normal(45, 5, 1000)
    c = coherent(M, T)
    assert np.allclose(c["home_pts"] - c["away_pts"], c["margin"], atol=1e-12)
    assert np.allclose(c["home_pts"] + c["away_pts"], c["total"], atol=1e-12)
    assert (c["home_pts"] >= 0).all() and (c["away_pts"] >= 0).all()


def test_infeasible_projection_is_flagged():
    c = coherent(np.array([50.0]), np.array([40.0]))
    assert c["projected"][0] and c["away_pts"][0] == 0.0 and c["home_pts"][0] == 40.0


def test_kickoff_converted_from_eastern_with_dst():
    g_sept = build_games(_sched())
    assert g_sept["kickoff_utc"][0] == datetime(2026, 9, 27, 17, 0, tzinfo=timezone.utc)
    g_dec = build_games(_sched(gameday="2026-12-06"))
    assert g_dec["kickoff_utc"][0] == datetime(2026, 12, 6, 18, 0, tzinfo=timezone.utc)


def test_neutral_site_and_franchise_alias():
    g = build_games(_sched(location="Neutral", home_team="OAK"))
    assert g["neutral_site"][0] and g["home_id"][0] == "LV"
