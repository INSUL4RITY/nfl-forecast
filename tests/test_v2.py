"""Model v2.0 inputs (features/v2.py) on small hand-made data."""

from datetime import datetime, timezone

import polars as pl
import pytest

from nflcast.features import v2 as V2
from nflcast.models.core import feature_set
from nflcast.predict import breakdown as BD


def _play(**kw):
    base = {"game_id": "G", "posteam": "KC", "defteam": "DEN", "play_type": "pass", "qb_dropback": 1, "qb_spike": 0,
            "qb_kneel": 0, "rush": 0, "wp": 0.5, "epa": 0.0, "yards_gained": 0, "qb_scramble": 0, "down": 1,
            "ydstogo": 10, "yardline_100": 75, "third_down_converted": 0, "fourth_down_converted": 0, "fumble": 0,
            "penalty": 0, "penalty_team": None}
    return {**base, **kw}


@pytest.fixture
def tg():
    return pl.DataFrame({"game_id": ["G", "G"], "team": ["KC", "DEN"], "opp": ["DEN", "KC"], "points": [24, 21],
                         "points_allowed": [21, 24], "plays": [4, 1]})


def test_garbage_filter_penalties_special_teams_and_close(tg):
    pbp = pl.DataFrame([
        _play(epa=1.0),
        _play(epa=5.0, wp=0.95, yards_gained=40),                       # garbage time: excluded from *_g sums
        _play(play_type="run", qb_dropback=0, rush=1, epa=0.5, down=3, third_down_converted=1),
        _play(qb_scramble=1, epa=0.8),
        _play(play_type="no_play", penalty=1, penalty_team="KC", epa=-0.6),    # offensive penalty (cancelled play)
        _play(play_type="no_play", penalty=1, penalty_team="DEN", epa=0.9),    # defensive penalty
        _play(play_type="punt", qb_dropback=0, epa=0.4, down=4, ydstogo=2, yardline_100=55),
        _play(play_type="field_goal", qb_dropback=0, posteam="DEN", defteam="KC", epa=-1.0),
        _play(posteam="DEN", defteam="KC", epa=0.2),
    ])
    out = V2.team_game_extra(pbp, tg).sort("team")
    kc, den = out.filter(pl.col("team") == "KC").row(0, named=True), out.filter(pl.col("team") == "DEN").row(0, named=True)
    assert kc["plays_g"] == 3 and kc["dropbacks_g"] == 2
    assert kc["epa_play_sum_g"] == pytest.approx(1.0 + 0.5 + 0.8)
    assert kc["expl_db_g"] == 0
    assert kc["scr_epa_sum"] == pytest.approx(0.8)
    assert (kc["third_att"], kc["third_conv"]) == (1, 1)
    assert kc["pen_off_epa_sum"] == pytest.approx(-0.6) and kc["pen_def_epa_sum"] == pytest.approx(0.9)
    assert (kc["go_opp"], kc["go_n"]) == (1, 0)
    assert kc["st_net"] == pytest.approx(0.4 - (-1.0)) and den["st_net"] == pytest.approx(-kc["st_net"])
    assert (kc["close_net"], den["close_net"]) == (1.0, -1.0)


def test_travel_and_body_clock():
    ko = datetime(2026, 11, 1, 18, 0, tzinfo=timezone.utc)          # 13:00 Eastern, 10:00 Pacific
    games = pl.DataFrame({"game_id": ["H1", "H2", "G"], "season": [2026] * 3, "kickoff_utc": [
        datetime(2026, 9, 13, 20, tzinfo=timezone.utc), datetime(2026, 9, 13, 20, tzinfo=timezone.utc), ko],
        "home_id": ["SEA", "NYJ", "NYJ"], "away_id": ["X1", "X2", "SEA"], "neutral_site": [False] * 3,
        "stadium_id": ["SEA00", "NYC01", "NYC01"], "kickoff_time_known": [True] * 3, "status": ["final", "final", "scheduled"]})
    coords = {"SEA00": (47.6, -122.3), "NYC01": (40.8, -74.1)}
    t = V2.travel_features(games, coords).filter(pl.col("game_id") == "G").row(0, named=True)
    assert t["home_travel_k"] == 0 and t["home_tz_shift"] == 0 and t["home_bc_early"] == 0
    assert t["away_tz_shift"] == 3 and t["away_bc_early"] == pytest.approx(3.0)
    assert 3.5 < t["away_travel_k"] < 4.0


def test_feature_set_and_breakdown_groups():
    fs = feature_set("v2")
    names = [f"team_{f}" for f in fs["team"]] + [f"opp_{f}" for f in fs["opp"]] + fs["context"]
    groups = {BD.group_of(n) for n in names}
    assert {"penalties", "special_teams", "injuries", "travel", "weather", "luck", "coaching"} <= groups
    v1 = feature_set("core_qb")
    v1_names = [f"team_{f}" for f in v1["team"]] + [f"opp_{f}" for f in v1["opp"]] + v1["context"]
    assert {BD.group_of(n) for n in v1_names} == {k for k, _ in BD.GROUPS[:9]} | {"other"}


def test_trial_artifact_is_recorded_frozen_and_never_official():
    from datetime import datetime, timezone
    from nflcast.predict import model_v2 as MV2
    rec = MV2.record()
    assert rec and rec["official"] is False and rec["feature_set"] == "v2.1"
    assert rec["preregistered_v2_0_test"]["pass"] is False
    m = MV2.load()                           # sha256 matches the recorded artifact
    assert m is not None and m["version"] == rec["version"]
    assert not MV2.is_official_for(datetime(2027, 1, 1, tzinfo=timezone.utc))
    fs = feature_set("v2.1")
    assert not set(V2.TRAVEL) & set(fs["team"] + fs["opp"])
