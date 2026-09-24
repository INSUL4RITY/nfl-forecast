"""As-of features must depend only on games available before the cutoff."""

from datetime import datetime, timedelta, timezone

import polars as pl

from nflcast.features.asof import AsOfFeatureBuilder
from tests.conftest import make_team_games


def _us(dt: datetime) -> int:
    return int(dt.timestamp() * 1_000_000)


def test_future_game_does_not_change_frozen_features(team_games):
    cutoff = datetime(2021, 9, 20, 12, 0, tzinfo=timezone.utc)
    before = AsOfFeatureBuilder(team_games).team_features("AAA", _us(cutoff), 2021)
    # Append games after the cutoff with extreme values.
    future = team_games.filter(pl.col("season") == 2021).with_columns(
        kickoff_utc=pl.col("kickoff_utc") + pl.duration(days=200),
        game_id=pl.col("game_id") + "_future",
        epa_play_sum=pl.lit(9999.0), points=pl.lit(99.0))
    after = AsOfFeatureBuilder(pl.concat([team_games, future])).team_features("AAA", _us(cutoff), 2021)
    assert before == after


def test_game_within_availability_lag_is_excluded(team_games):
    # A game kicking off 2h before the cutoff is not yet available (lag 12h), so features equal
    # those computed from a table without that game.
    ko = team_games.filter(pl.col("season") == 2021)["kickoff_utc"].max()
    cutoff = ko + timedelta(hours=2)
    full = AsOfFeatureBuilder(team_games).team_features("AAA", _us(cutoff), 2021)
    without = AsOfFeatureBuilder(team_games.filter(pl.col("kickoff_utc") != ko)).team_features("AAA", _us(cutoff), 2021)
    assert full == without


def test_game_after_lag_is_included(team_games):
    ko = team_games.filter(pl.col("season") == 2021)["kickoff_utc"].max()
    cutoff = ko + timedelta(hours=13)
    full = AsOfFeatureBuilder(team_games).team_features("AAA", _us(cutoff), 2021)
    without = AsOfFeatureBuilder(team_games.filter(pl.col("kickoff_utc") != ko)).team_features("AAA", _us(cutoff), 2021)
    assert full["games_hist"] == without["games_hist"] + 1


def test_week1_features_come_from_prior_season_only():
    tg = make_team_games()
    first_2021 = tg.filter(pl.col("season") == 2021)["kickoff_utc"].min()
    f = AsOfFeatureBuilder(tg).team_features("AAA", _us(first_2021 - timedelta(hours=72)), 2021)
    assert f["games_this_season"] == 0
    assert f["games_hist"] > 0
