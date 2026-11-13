from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl
import pytest

from nflcast.predict import release as R

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)


def _games():
    ko = [NOW - timedelta(days=7 * i) for i in range(1, 6)] + [NOW + timedelta(days=3)]
    return pl.DataFrame({"season": [2025] * 5 + [2026], "status": ["final"] * 5 + ["scheduled"], "kickoff_utc": ko,
                         "stadium_id": ["ATL97"] * 5 + ["ATL97"],
                         "roof": ["closed", "closed", "closed", "open", "dome", ""]})


def test_closed_share_uses_only_finished_games_before_now():
    assert R.roof_closed_share(_games(), NOW) == {"ATL97": pytest.approx(0.8)}


def test_blank_roof_gets_the_stadium_share_and_known_roofs_are_unchanged():
    shares = {"ATL97": 0.8}
    assert R.dome_input("", "ATL97", shares) == (pytest.approx(0.8), "stadium closed share (roof not yet set)")
    assert R.dome_input(None, "ATL97", shares)[0] == pytest.approx(0.8)
    assert R.dome_input("closed", "ATL97", shares) == (1.0, "schedule roof")
    assert R.dome_input("dome", "X", shares) == (1.0, "schedule roof")
    assert R.dome_input("outdoors", "X", shares) == (0.0, "schedule roof")
    assert R.dome_input("", "NEW00", shares) == (0.0, "roof not set; no stadium history")


def test_roof_input_moves_the_frozen_total_not_the_margin():
    """The frozen football-only model treats dome as game context for both team rows: it changes the total only."""
    from nflcast.predict import freeze
    if not freeze.is_frozen():
        pytest.skip("no frozen artifact")
    bmod = freeze.load()["bmod"]
    fs = bmod.feature_set
    row = {f"{s}_{f}": 0.0 for s in ("home", "away") for f in fs["team"] + fs["opp"]}
    row.update({"neutral_site": False, "rest_diff": 0, "is_playoff": False, "home_games_this_season": 9.0,
                "away_games_this_season": 9.0})
    base = {**row, **{k: 0.0 for k in fs["context"] if k not in row}}
    p0 = bmod.predict(pl.DataFrame([{**base, "dome": 0.0}]))
    p1 = bmod.predict(pl.DataFrame([{**base, "dome": 0.8}]))
    assert np.allclose(p0["margin"], p1["margin"])
    assert p1["total"][0] - p0["total"][0] == pytest.approx(0.8 * 2.78, abs=0.05)
